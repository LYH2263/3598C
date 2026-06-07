from decimal import Decimal, ROUND_HALF_UP

from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase, TransactionTestCase
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

try:
    from hypothesis import given, settings, HealthCheck
    from hypothesis.strategies import decimals, lists
    from hypothesis.extra.django import TestCase as HypothesisDjangoTestCase
    HAS_HYPOTHESIS = True
except ImportError:
    HAS_HYPOTHESIS = False

from accounts.models import Profile
from billing.models import (
    BalanceChangeLog,
    ConsumptionRecord,
    RechargeOrder,
    RechargeRecord,
    Wallet,
)
from billing.services.ledger_service import LedgerService


def _create_student(username='student_user', password='Student@123456',
                    balance: Decimal = Decimal('0.00')):
    user = User.objects.create_user(username=username, password=password, email=f'{username}@test.com')
    profile = Profile.objects.create(
        user=user,
        role=Profile.ROLE_STUDENT,
        student_id='2026' + username[-4:],
        phone='138' + username[-8:],
        security_question='测试问题',
    )
    profile.set_security_answer('答案')
    profile.save(update_fields=['security_answer_hash'])
    Wallet.objects.create(user=user, balance=Decimal(balance))
    return user


def _create_admin(username='admin_user', password='Admin@123456'):
    user = User.objects.create_user(username=username, password=password, email=f'{username}@test.com')
    Profile.objects.create(user=user, role=Profile.ROLE_ADMIN, phone='139' + username[-8:])
    Wallet.objects.create(user=user)
    return user


def _assert_log_chain_consistent(user, expected_final_balance: Decimal | None = None):
    logs = list(BalanceChangeLog.objects.filter(user=user).order_by('created_at', 'id'))
    if not logs:
        return

    running = logs[0].balance_before
    for log in logs:
        assert log.balance_before == running, (
            f'Log id={log.id} balance_before={log.balance_before} '
            f'!= expected running={running}'
        )
        expected_after = (running + log.amount_delta).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
        assert log.balance_after == expected_after, (
            f'Log id={log.id} balance_after={log.balance_after} '
            f'!= computed {expected_after} (before={running}, delta={log.amount_delta})'
        )
        running = log.balance_after

    wallet = Wallet.objects.get(user=user)
    assert wallet.balance == running, (
        f'Wallet balance={wallet.balance} != final log chain balance={running}'
    )
    if expected_final_balance is not None:
        assert wallet.balance == expected_final_balance.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


# ---------------------------------------------------------------------------
# Service 层：_money 四舍五入单元测试
# ---------------------------------------------------------------------------


class LedgerServiceMoneyRoundingTests(TestCase):
    def test_money_round_half_up_positive(self):
        self.assertEqual(LedgerService._money(Decimal('0.005')), Decimal('0.01'))
        self.assertEqual(LedgerService._money(Decimal('0.015')), Decimal('0.02'))
        self.assertEqual(LedgerService._money(Decimal('1.234')), Decimal('1.23'))
        self.assertEqual(LedgerService._money(Decimal('1.235')), Decimal('1.24'))
        self.assertEqual(LedgerService._money(Decimal('100.004')), Decimal('100.00'))
        self.assertEqual(LedgerService._money(Decimal('100.005')), Decimal('100.01'))

    def test_money_round_half_up_negative(self):
        self.assertEqual(LedgerService._money(Decimal('-0.005')), Decimal('-0.01'))
        self.assertEqual(LedgerService._money(Decimal('-1.235')), Decimal('-1.24'))

    def test_money_already_quantized(self):
        self.assertEqual(LedgerService._money(Decimal('0.00')), Decimal('0.00'))
        self.assertEqual(LedgerService._money(Decimal('99.99')), Decimal('99.99'))

    def test_money_accepts_string(self):
        self.assertEqual(LedgerService._money('0.005'), Decimal('0.01'))


# ---------------------------------------------------------------------------
# Service 层：充值/消费金额校验
# ---------------------------------------------------------------------------


class LedgerServiceAmountValidationTests(TestCase):
    def setUp(self):
        self.student = _create_student('val_stu', balance=Decimal('50.00'))
        self.admin = _create_admin('val_adm')

    def test_recharge_zero_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            LedgerService.create_recharge(
                user=self.student, amount=Decimal('0.00'),
                channel='wechat', operator=self.admin.username,
            )
        self.assertIn('大于 0', str(ctx.exception))

    def test_recharge_negative_rejected(self):
        with self.assertRaises(ValidationError):
            LedgerService.create_recharge(
                user=self.student, amount=Decimal('-10.00'),
                channel='wechat', operator=self.admin.username,
            )

    def test_recharge_order_zero_rejected(self):
        with self.assertRaises(ValidationError):
            LedgerService.create_recharge_order(
                user=self.student, amount=Decimal('0'), channel='alipay',
            )

    def test_consumption_usage_zero_rejected(self):
        with self.assertRaises(ValidationError) as ctx:
            LedgerService.create_consumption(
                user=self.student, category='water',
                usage=Decimal('0.00'), unit_price=Decimal('1.00'),
                meter_value=None, operator=self.admin.username,
            )
        self.assertIn('大于 0', str(ctx.exception))

    def test_consumption_unit_price_zero_rejected(self):
        with self.assertRaises(ValidationError):
            LedgerService.create_consumption(
                user=self.student, category='electricity',
                usage=Decimal('5.00'), unit_price=Decimal('0.00'),
                meter_value=None, operator=self.admin.username,
            )

    def test_consumption_both_negative_rejected(self):
        with self.assertRaises(ValidationError):
            LedgerService.create_consumption(
                user=self.student, category='water',
                usage=Decimal('-1.00'), unit_price=Decimal('-1.00'),
                meter_value=None, operator=self.admin.username,
            )


# ---------------------------------------------------------------------------
# Service 层：消费时余额不足 → 事务回滚（不产生任何记录）
# ---------------------------------------------------------------------------


class LedgerServiceInsufficientBalanceRollbackTests(TransactionTestCase):
    def setUp(self):
        self.student = _create_student('rollback_stu', balance=Decimal('10.00'))
        self.admin = _create_admin('rollback_adm')

    def test_insufficient_balance_rejects_and_writes_nothing(self):
        wallet_before = Wallet.objects.get(user=self.student)
        log_count_before = BalanceChangeLog.objects.filter(user=self.student).count()
        cons_count_before = ConsumptionRecord.objects.filter(user=self.student).count()

        with self.assertRaises(ValidationError) as ctx:
            LedgerService.create_consumption(
                user=self.student, category='electricity',
                usage=Decimal('20.00'), unit_price=Decimal('1.00'),
                meter_value=Decimal('100.00'), operator=self.admin.username,
            )
        self.assertIn('余额不足', str(ctx.exception))

        self.student.wallet.refresh_from_db()
        self.assertEqual(self.student.wallet.balance, wallet_before.balance)
        self.assertEqual(
            BalanceChangeLog.objects.filter(user=self.student).count(),
            log_count_before,
        )
        self.assertEqual(
            ConsumptionRecord.objects.filter(user=self.student).count(),
            cons_count_before,
        )

    def test_insufficient_balance_boundary(self):
        with self.assertRaises(ValidationError):
            LedgerService.create_consumption(
                user=self.student, category='water',
                usage=Decimal('10.01'), unit_price=Decimal('1.00'),
                meter_value=None, operator=self.admin.username,
            )
        self.student.wallet.refresh_from_db()
        self.assertEqual(self.student.wallet.balance, Decimal('10.00'))

    def test_exact_balance_succeeds(self):
        record = LedgerService.create_consumption(
            user=self.student, category='water',
            usage=Decimal('10.00'), unit_price=Decimal('1.00'),
            meter_value=None, operator=self.admin.username,
        )
        self.assertEqual(record.cost_amount, Decimal('10.00'))
        self.student.wallet.refresh_from_db()
        self.assertEqual(self.student.wallet.balance, Decimal('0.00'))
        _assert_log_chain_consistent(self.student, Decimal('0.00'))


# ---------------------------------------------------------------------------
# Service 层：冻结状态拦截
# ---------------------------------------------------------------------------


class LedgerServiceFrozenWalletTests(TestCase):
    def setUp(self):
        self.student = _create_student('frozen_stu', balance=Decimal('100.00'))
        self.admin = _create_admin('frozen_adm')
        LedgerService.freeze_wallet(self.student, operator=self.admin.username, reason='测试冻结')

    def test_frozen_blocks_recharge(self):
        with self.assertRaises(ValidationError) as ctx:
            LedgerService.create_recharge(
                user=self.student, amount=Decimal('50.00'),
                channel='wechat', operator=self.admin.username,
            )
        self.assertIn('冻结', str(ctx.exception))

    def test_frozen_blocks_recharge_order(self):
        with self.assertRaises(ValidationError) as ctx:
            LedgerService.create_recharge_order(
                user=self.student, amount=Decimal('30.00'), channel='alipay',
            )
        self.assertIn('冻结', str(ctx.exception))

    def test_frozen_blocks_consumption(self):
        with self.assertRaises(ValidationError) as ctx:
            LedgerService.create_consumption(
                user=self.student, category='water',
                usage=Decimal('5.00'), unit_price=Decimal('1.00'),
                meter_value=None, operator=self.admin.username,
            )
        self.assertIn('冻结', str(ctx.exception))

    def test_frozen_balance_unchanged(self):
        self.student.wallet.refresh_from_db()
        self.assertEqual(self.student.wallet.balance, Decimal('100.00'))
        self.assertTrue(self.student.wallet.is_frozen)

    def test_unfreeze_restores_operations(self):
        LedgerService.unfreeze_wallet(self.student, operator=self.admin.username, reason='测试解冻')
        self.student.wallet.refresh_from_db()
        self.assertFalse(self.student.wallet.is_frozen)

        record = LedgerService.create_recharge(
            user=self.student, amount=Decimal('25.00'),
            channel='bank', operator=self.admin.username,
        )
        self.assertEqual(record.amount, Decimal('25.00'))
        self.student.wallet.refresh_from_db()
        self.assertEqual(self.student.wallet.balance, Decimal('125.00'))
        _assert_log_chain_consistent(self.student, Decimal('125.00'))


# ---------------------------------------------------------------------------
# Service 层：freeze / unfreeze 幂等
# ---------------------------------------------------------------------------


class LedgerServiceFreezeIdempotencyTests(TestCase):
    def setUp(self):
        self.student = _create_student('idem_stu', balance=Decimal('60.00'))
        self.admin = _create_admin('idem_adm')

    def test_double_freeze_writes_only_one_log(self):
        w1 = LedgerService.freeze_wallet(self.student, self.admin.username, '首次冻结')
        self.assertTrue(w1.is_frozen)

        freeze_logs_before = BalanceChangeLog.objects.filter(
            user=self.student, change_type=BalanceChangeLog.TYPE_FREEZE,
        ).count()
        self.assertEqual(freeze_logs_before, 1)

        w2 = LedgerService.freeze_wallet(self.student, self.admin.username, '重复冻结')
        self.assertTrue(w2.is_frozen)

        freeze_logs_after = BalanceChangeLog.objects.filter(
            user=self.student, change_type=BalanceChangeLog.TYPE_FREEZE,
        ).count()
        self.assertEqual(freeze_logs_after, 1)

        _assert_log_chain_consistent(self.student, Decimal('60.00'))

    def test_double_unfreeze_writes_only_one_log(self):
        LedgerService.freeze_wallet(self.student, self.admin.username, '冻结')
        unfreeze_logs_before = BalanceChangeLog.objects.filter(
            user=self.student, change_type=BalanceChangeLog.TYPE_UNFREEZE,
        ).count()
        self.assertEqual(unfreeze_logs_before, 0)

        LedgerService.unfreeze_wallet(self.student, self.admin.username, '首次解冻')
        unfreeze_logs_mid = BalanceChangeLog.objects.filter(
            user=self.student, change_type=BalanceChangeLog.TYPE_UNFREEZE,
        ).count()
        self.assertEqual(unfreeze_logs_mid, 1)

        LedgerService.unfreeze_wallet(self.student, self.admin.username, '重复解冻')
        unfreeze_logs_after = BalanceChangeLog.objects.filter(
            user=self.student, change_type=BalanceChangeLog.TYPE_UNFREEZE,
        ).count()
        self.assertEqual(unfreeze_logs_after, 1)

        _assert_log_chain_consistent(self.student, Decimal('60.00'))


# ---------------------------------------------------------------------------
# Service 层：日志链不变量（balance_before/after 与钱包余额一致）
# ---------------------------------------------------------------------------


class LedgerServiceBalanceLogInvariantTests(TestCase):
    def setUp(self):
        self.student = _create_student('inv_stu', balance=Decimal('0.00'))
        self.admin = _create_admin('inv_adm')

    def test_mixed_operations_preserve_log_chain(self):
        LedgerService.create_recharge(
            user=self.student, amount=Decimal('0.005'),
            channel='wechat', operator=self.admin.username,
        )
        _assert_log_chain_consistent(self.student, Decimal('0.01'))

        LedgerService.create_recharge(
            user=self.student, amount=Decimal('99.99'),
            channel='alipay', operator=self.admin.username,
        )
        _assert_log_chain_consistent(self.student, Decimal('100.00'))

        LedgerService.create_consumption(
            user=self.student, category='water',
            usage=Decimal('10.00'), unit_price=Decimal('2.345'),
            meter_value=None, operator=self.admin.username,
        )
        _assert_log_chain_consistent(self.student)

        LedgerService.freeze_wallet(self.student, self.admin.username, '违规')
        _assert_log_chain_consistent(self.student)

        LedgerService.unfreeze_wallet(self.student, self.admin.username, '恢复')
        _assert_log_chain_consistent(self.student)

    def test_recharge_order_review_chain(self):
        order = LedgerService.create_recharge_order(
            user=self.student, amount=Decimal('50.505'), channel='bank',
        )
        LedgerService.review_recharge_order(
            order=order, action=RechargeOrder.STATUS_APPROVED,
            reviewer=self.admin, review_remark='通过',
        )
        _assert_log_chain_consistent(self.student, Decimal('50.51'))

    def test_rejected_order_does_not_write_log(self):
        order = LedgerService.create_recharge_order(
            user=self.student, amount=Decimal('30.00'), channel='wechat',
        )
        LedgerService.review_recharge_order(
            order=order, action=RechargeOrder.STATUS_REJECTED,
            reviewer=self.admin, review_remark='驳回',
        )
        self.student.wallet.refresh_from_db()
        self.assertEqual(self.student.wallet.balance, Decimal('0.00'))
        self.assertEqual(
            BalanceChangeLog.objects.filter(user=self.student).count(), 0,
        )


# ---------------------------------------------------------------------------
# API 层：权限控制集成测试
# ---------------------------------------------------------------------------


class BillingAPIPermissionTests(TestCase):
    def setUp(self):
        self.student = _create_student('perm_stu', balance=Decimal('50.00'))
        self.admin = _create_admin('perm_adm')
        self.student_client = APIClient()
        self.student_client.force_authenticate(self.student)
        self.admin_client = APIClient()
        self.admin_client.force_authenticate(self.admin)

    def test_student_cannot_review_recharge_order(self):
        order = LedgerService.create_recharge_order(
            user=self.student, amount=Decimal('20.00'), channel='wechat',
        )
        resp = self.student_client.post(
            f'/api/billing/recharge-orders/{order.id}/review/',
            {'action': 'approved', 'review_remark': '学生尝试通过'},
            format='json',
        )
        self.assertEqual(resp.status_code, 403)
        order.refresh_from_db()
        self.assertEqual(order.status, RechargeOrder.STATUS_PENDING)

    def test_student_cannot_freeze_wallet(self):
        resp = self.student_client.post(
            f'/api/billing/wallets/{self.student.id}/action/',
            {'action': 'freeze', 'reason': '学生自冻'},
            format='json',
        )
        self.assertEqual(resp.status_code, 403)
        self.student.wallet.refresh_from_db()
        self.assertFalse(self.student.wallet.is_frozen)

    def test_student_cannot_unfreeze_wallet(self):
        LedgerService.freeze_wallet(self.student, operator=self.admin.username)
        resp = self.student_client.post(
            f'/api/billing/wallets/{self.student.id}/action/',
            {'action': 'unfreeze', 'reason': '学生自解'},
            format='json',
        )
        self.assertEqual(resp.status_code, 403)
        self.student.wallet.refresh_from_db()
        self.assertTrue(self.student.wallet.is_frozen)

    def test_admin_can_freeze_and_unfreeze(self):
        resp = self.admin_client.post(
            f'/api/billing/wallets/{self.student.id}/action/',
            {'action': 'freeze', 'reason': '管理员冻结'},
            format='json',
        )
        self.assertEqual(resp.status_code, 200)
        self.student.wallet.refresh_from_db()
        self.assertTrue(self.student.wallet.is_frozen)

        resp = self.admin_client.post(
            f'/api/billing/wallets/{self.student.id}/action/',
            {'action': 'unfreeze', 'reason': '管理员解冻'},
            format='json',
        )
        self.assertEqual(resp.status_code, 200)
        self.student.wallet.refresh_from_db()
        self.assertFalse(self.student.wallet.is_frozen)


# ---------------------------------------------------------------------------
# API 层：冻结钱包拦截集成测试
# ---------------------------------------------------------------------------


class BillingAPIFrozenWalletTests(TestCase):
    def setUp(self):
        self.student = _create_student('api_frozen_stu', balance=Decimal('80.00'))
        self.admin = _create_admin('api_frozen_adm')
        self.student_client = APIClient()
        self.student_client.force_authenticate(self.student)
        self.admin_client = APIClient()
        self.admin_client.force_authenticate(self.admin)

        LedgerService.freeze_wallet(self.student, operator=self.admin.username, reason='冻结')

    def test_frozen_blocks_recharge_order_api(self):
        resp = self.student_client.post(
            '/api/billing/recharge-orders/',
            {'amount': '50.00', 'channel': 'wechat', 'submit_remark': '尝试充值'},
            format='json',
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn('冻结', str(resp.json()))

    def test_frozen_blocks_direct_recharge_api(self):
        resp = self.admin_client.post(
            '/api/billing/recharges/',
            {'user_id': self.student.id, 'amount': '30.00', 'channel': 'alipay'},
            format='json',
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn('冻结', str(resp.json()))

    def test_frozen_blocks_consumption_api(self):
        resp = self.admin_client.post(
            '/api/billing/consumptions/',
            {
                'user_id': self.student.id,
                'category': 'water',
                'usage': '5.00',
                'unit_price': '1.00',
            },
            format='json',
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn('冻结', str(resp.json()))


# ---------------------------------------------------------------------------
# 回归：覆盖主路径的原有测试
# ---------------------------------------------------------------------------


class BillingFlowRegressionTests(TestCase):
    def setUp(self):
        self.admin = _create_admin('flow_adm')
        self.student = _create_student('flow_stu', balance=Decimal('100.00'))
        self.admin_client = APIClient()
        self.admin_client.force_authenticate(self.admin)
        self.student_client = APIClient()
        self.student_client.force_authenticate(self.student)

    def test_student_order_admin_approve_updates_balance_and_log(self):
        resp = self.student_client.post(
            '/api/billing/recharge-orders/',
            {'amount': '50.00', 'channel': 'wechat', 'submit_remark': '测试充值'},
            format='json',
        )
        self.assertEqual(resp.status_code, 201)
        order_id = resp.json()['id']

        review_resp = self.admin_client.post(
            f'/api/billing/recharge-orders/{order_id}/review/',
            {'action': 'approved', 'review_remark': '通过'},
            format='json',
        )
        self.assertEqual(review_resp.status_code, 200)

        self.student.wallet.refresh_from_db()
        self.assertEqual(self.student.wallet.balance, Decimal('150.00'))
        self.assertTrue(
            BalanceChangeLog.objects.filter(
                user=self.student, change_type=BalanceChangeLog.TYPE_RECHARGE,
            ).exists()
        )
        _assert_log_chain_consistent(self.student, Decimal('150.00'))

    def test_frozen_wallet_blocks_order_submission(self):
        LedgerService.freeze_wallet(self.student, operator=self.admin.username, reason='测试冻结')
        resp = self.student_client.post(
            '/api/billing/recharge-orders/',
            {'amount': '20.00', 'channel': 'alipay'},
            format='json',
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn('账户已冻结', str(resp.json()))


class AnnouncementPushRegressionTests(TestCase):
    def setUp(self):
        self.admin = _create_admin('not_adm')
        self.student = _create_student('not_stu')
        self.client = APIClient()

    def test_publish_announcement_pushes_notifications(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.post(
            '/api/notices/announcements/',
            {'title': '测试公告', 'content': '公告内容', 'is_active': True},
            format='json',
        )
        self.assertEqual(resp.status_code, 201)

        self.client.force_authenticate(self.student)
        notice_resp = self.client.get('/api/notices/notifications/')
        self.assertEqual(notice_resp.status_code, 200)
        self.assertGreaterEqual(notice_resp.json()['unread_count'], 1)


# ---------------------------------------------------------------------------
# 基于属性的测试：连续多笔随机充值后，日志逐笔累加余额恒等于钱包余额
# ---------------------------------------------------------------------------


if HAS_HYPOTHESIS:
    class LedgerServicePropertyBasedTests(HypothesisDjangoTestCase):
        def _reset_schema(self):
            pass

        @given(
            amounts=lists(
                decimals(min_value='0.01', max_value='999.99', allow_nan=False, allow_infinity=False),
                min_size=1, max_size=15,
            )
        )
        @settings(
            max_examples=10,
            suppress_health_check=[HealthCheck.function_scoped_fixture],
            deadline=None,
        )
        def test_random_recharges_log_chain_matches_wallet(self, amounts):
            user = User.objects.create_user(
                username=f'prop_{id(self)}_{len(amounts)}',
                password='T@est1234',
                email=f'prop_{id(self)}_{len(amounts)}@test.com',
            )
            Profile.objects.create(
                user=user, role=Profile.ROLE_STUDENT,
                student_id=f'P{user.id}', phone=f'170{user.id:08d}',
            )
            Wallet.objects.create(user=user, balance=Decimal('0.00'))

            admin = User.objects.create_user(
                username=f'prop_adm_{id(self)}_{len(amounts)}',
                password='T@est1234',
                email=f'prop_adm_{id(self)}_{len(amounts)}@test.com',
            )
            Profile.objects.create(user=admin, role=Profile.ROLE_ADMIN, phone=f'171{admin.id:08d}')
            Wallet.objects.create(user=admin)

            expected = Decimal('0.00')
            for amt in amounts:
                amt_q = Decimal(str(amt)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                if amt_q <= 0:
                    continue
                LedgerService.create_recharge(
                    user=user, amount=amt_q, channel='wechat', operator=admin.username,
                )
                expected = (expected + amt_q).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)

            user.wallet.refresh_from_db()
            self.assertEqual(user.wallet.balance, expected)

            logs = list(BalanceChangeLog.objects.filter(user=user).order_by('created_at', 'id'))
            self.assertEqual(len(logs), len([a for a in amounts if Decimal(str(a)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP) > 0]))

            running = Decimal('0.00')
            for log in logs:
                self.assertEqual(log.balance_before, running)
                expected_after = (running + log.amount_delta).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
                self.assertEqual(log.balance_after, expected_after)
                running = log.balance_after
            self.assertEqual(running, user.wallet.balance)

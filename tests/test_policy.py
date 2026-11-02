from safedesk.config import TenantConfig
from safedesk.policy import PolicyEngine
from safedesk.session import Session
from safedesk.store import Store, refund_eligibility


def setup():
    store = Store()
    tenant = TenantConfig.load()
    return store, tenant, PolicyEngine(store, tenant)


def test_account_tools_require_verification():
    _, _, policy = setup()
    decision = policy.check("get_order_status", {"order_id": "A1001"}, Session())
    assert not decision.allowed and decision.reason == "identity_not_verified"


def test_cannot_touch_another_customers_order():
    _, _, policy = setup()
    session = Session(verified_customer_id="C001")
    decision = policy.check("get_order_status", {"order_id": "A1003"}, session)
    assert decision.reason == "order_not_owned_by_verified_customer"


def test_refund_over_limit_routes_to_human():
    _, _, policy = setup()
    session = Session(verified_customer_id="C002")
    decision = policy.check("issue_refund", {"order_id": "A1004"}, session)
    assert not decision.allowed and decision.route_to_human and decision.reason == "amount_over_auto_limit"


def test_high_risk_session_blocks_refund_even_when_verified():
    _, _, policy = setup()
    session = Session(verified_customer_id="C001", risk_categories={"payout_redirect", "urgency"})
    decision = policy.check("issue_refund", {"order_id": "A1002"}, session)
    assert decision.reason == "social_engineering_risk"


def test_verification_lockout():
    _, tenant, policy = setup()
    session = Session(failed_verifications=tenant.max_verification_attempts)
    assert policy.check("verify_identity", {"email": "x@y.com", "order_id": "A1001"}, session).reason == "verification_locked"


def test_eligibility_rules():
    store, tenant, _ = setup()
    assert refund_eligibility(store.get_order("A1002"), tenant)["eligible"]
    assert refund_eligibility(store.get_order("A1003"), tenant)["reason"] == "outside_window"
    assert refund_eligibility(store.get_order("A1005"), tenant)["reason"] == "final_sale"
    assert refund_eligibility(store.get_order("A1001"), tenant)["reason"] == "not_delivered"


def test_tenant_config_changes_policy_without_code():
    store = Store()
    strict = TenantConfig.load("andes_coffee_co.json")
    # A1002 ($129, delivered 13 days ago) is inside both tenants' windows.
    assert refund_eligibility(store.get_order("A1002"), strict)["eligible"]
    # A1005-style late orders: A1003 was delivered 48 days ago, outside both windows.
    assert refund_eligibility(store.get_order("A1003"), strict)["reason"] == "outside_window"
    # A1004 ($899, 5 days) is eligible at both, and both require a human, at different limits.
    assert strict.auto_refund_limit == 150.0
    assert refund_eligibility(store.get_order("A1004"), strict)["requires_human"]

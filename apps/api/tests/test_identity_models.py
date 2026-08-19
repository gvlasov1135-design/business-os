from modules.identity.models import AuditEvent, Company, Department, Role, User, user_roles


def test_identity_table_names():
    assert Company.__tablename__ == "companies"
    assert Role.__tablename__ == "roles"
    assert User.__tablename__ == "users"
    assert Department.__tablename__ == "departments"
    assert AuditEvent.__tablename__ == "audit_events"
    assert user_roles.name == "user_roles"

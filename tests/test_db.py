from flask import url_for


def test_get_all_user(client, db, user_factory, admin_headers):
    users_url = url_for('api.users')
    users = user_factory.create_batch(30)

    db.session.add_all(users)
    db.session.commit()

    rep = client.get(users_url, headers=admin_headers)
    assert rep.status_code == 200

    results = rep.get_json()
    for user in users:
        assert any(u["id"] == user.id for u in results["results"])

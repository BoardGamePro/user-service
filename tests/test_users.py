import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from sqlalchemy import text

@pytest.mark.asyncio
async def test_register_and_login_and_no_id_in_response(db_session):
    async with db_session() as db:
        await db.execute(text('DELETE FROM tokens'))
        await db.execute(text('DELETE FROM users'))
        await db.commit()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Регистрация
        resp = await ac.post("/auth/register", json={
            "username": "testuser",
            "email": "testuser@example.com",
            "password": "Test1234",
            "role": "user"
        })
        assert resp.status_code == 201
        data = resp.json()
        assert "id" not in data
        assert data["username"] == "testuser"
        # Логин
        resp = await ac.post("/auth/login", json={
            "username": "testuser",
            "password": "Test1234"
        })
        assert resp.status_code == 200
        # Проверка refresh токена в куки
        assert "refresh_token" in resp.cookies
        # Проверка access_token в теле
        assert "access_token" in resp.json()

@pytest.mark.asyncio
async def test_change_email_and_username_and_password(db_session):
    async with db_session() as db:
        await db.execute(text('DELETE FROM tokens'))
        await db.execute(text('DELETE FROM users'))
        await db.commit()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Регистрация и логин
        await ac.post("/auth/register", json={
            "username": "user2",
            "email": "user2@example.com",
            "password": "Test1234",
            "role": "user"
        })
        login = await ac.post("/auth/login", json={
            "username": "user2",
            "password": "Test1234"
        })
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        # Смена email
        resp = await ac.patch("/users/me/email", json={"new_email": "user2new@example.com"}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["email"] == "user2new@example.com"
        # Смена username
        resp = await ac.patch("/users/me/username", json={"new_username": "user2new"}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["username"] == "user2new"
        # Смена пароля
        resp = await ac.patch("/users/me/password", json={"current_password": "Test1234", "new_password": "Newpass123"}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["detail"] == "Пароль изменён"

@pytest.mark.asyncio
async def test_logout_and_delete_account(db_session):
    async with db_session() as db:
        await db.execute(text('DELETE FROM tokens'))
        await db.execute(text('DELETE FROM users'))
        await db.commit()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.post("/auth/register", json={
            "username": "user3",
            "email": "user3@example.com",
            "password": "Test1234",
            "role": "user"
        })
        login = await ac.post("/auth/login", json={
            "username": "user3",
            "password": "Test1234"
        })
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        # Логаут
        resp = await ac.post("/users/logout", headers=headers)
        assert resp.status_code == 200
        # Удаление аккаунта
        resp = await ac.delete("/users/me", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["detail"] == "Account deleted"

@pytest.mark.asyncio
async def test_get_me_and_user_profile(db_session):
    async with db_session() as db:
        await db.execute(text('DELETE FROM tokens'))
        await db.execute(text('DELETE FROM users'))
        await db.commit()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.post("/auth/register", json={
            "username": "profileuser",
            "email": "profileuser@example.com",
            "password": "Test1234",
            "role": "user"
        })
        login = await ac.post("/auth/login", json={
            "username": "profileuser",
            "password": "Test1234"
        })
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        # /users/me
        resp = await ac.get("/users/me", headers=headers)
        assert resp.status_code == 200
        assert resp.json()["username"] == "profileuser"
        # /users/{username}
        resp = await ac.get("/users/profileuser")
        assert resp.status_code == 200
        assert resp.json()["username"] == "profileuser"

@pytest.mark.asyncio
async def test_change_profile_and_list_users(db_session):
    async with db_session() as db:
        await db.execute(text('DELETE FROM tokens'))
        await db.execute(text('DELETE FROM users'))
        await db.commit()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.post("/auth/register", json={
            "username": "listuser",
            "email": "listuser@example.com",
            "password": "Test1234",
            "role": "user"
        })
        login = await ac.post("/auth/login", json={
            "username": "listuser",
            "password": "Test1234"
        })
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        # /users/me/profile
        resp = await ac.patch("/users/me/profile", json={"bio": "bio text", "is_profile_public": False}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["bio"] == "bio text"
        # /users/
        resp = await ac.get("/users/")
        assert resp.status_code == 200
        assert any(u["username"] == "listuser" for u in resp.json())

@pytest.mark.asyncio
async def test_refresh_token(db_session):
    async with db_session() as db:
        await db.execute(text('DELETE FROM tokens'))
        await db.execute(text('DELETE FROM users'))
        await db.commit()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.post("/auth/register", json={
            "username": "refreshuser",
            "email": "refreshuser@example.com",
            "password": "Test1234",
            "role": "user"
        })
        login = await ac.post("/auth/login", json={
            "username": "refreshuser",
            "password": "Test1234"
        })
        refresh_token = login.cookies.get("refresh_token")
        resp = await ac.post("/auth/refresh", json={"refresh_token": refresh_token})
        assert resp.status_code == 200
        assert "access_token" in resp.json()

@pytest.mark.asyncio
async def test_password_reset(db_session):
    async with db_session() as db:
        await db.execute(text('DELETE FROM tokens'))
        await db.execute(text('DELETE FROM users'))
        await db.commit()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.post("/auth/register", json={
            "username": "resetuser",
            "email": "resetuser@example.com",
            "password": "Test1234",
            "role": "user"
        })
        # Запрос на сброс пароля
        resp = await ac.post("/auth/request-password-reset", json={"email": "resetuser@example.com"})
        assert resp.status_code == 200
        # Тестовый сброс пароля невозможен без реального email/token, но endpoint покрыт

@pytest.mark.asyncio
async def test_change_password(db_session):
    async with db_session() as db:
        await db.execute(text('DELETE FROM tokens'))
        await db.execute(text('DELETE FROM users'))
        await db.commit()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        await ac.post("/auth/register", json={
            "username": "changepass",
            "email": "changepass@example.com",
            "password": "Test1234",
            "role": "user"
        })
        login = await ac.post("/auth/login", json={
            "username": "changepass",
            "password": "Test1234"
        })
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        resp = await ac.patch("/users/me/password", json={"current_password": "Test1234", "new_password": "Newpass123"}, headers=headers)
        assert resp.status_code == 200
        assert resp.json()["detail"] == "Пароль изменён"

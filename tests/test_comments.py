import uuid

import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app


@pytest.mark.asyncio
async def test_get_comments_empty(db_session, setup_clean_test_data):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/comments/", params={"game_name": "Monopoly", "page": "1"})
        assert resp.status_code == 200
        assert resp.json() == []


@pytest.mark.asyncio
async def test_create_and_get_comments(db_session, setup_clean_test_data):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Регистрация и логин пользователя 1
        reg1 = await ac.post("/auth/register", json={
            "username": "user1",
            "email": "user1@example.com",
            "password": "Test1234"
        })
        user1_id = reg1.json()["id"]
        login1 = await ac.post("/auth/login", json={
            "username": "user1",
            "password": "Test1234"
        })
        token1 = login1.json()["access_token"]
        headers1 = {"Authorization": f"Bearer {token1}"}

        # Регистрация и логин пользователя 2
        reg2 = await ac.post("/auth/register", json={
            "username": "user2",
            "email": "user2@example.com",
            "password": "Test1234"
        })
        user2_id = reg2.json()["id"]
        login2 = await ac.post("/auth/login", json={
            "username": "user2",
            "password": "Test1234"
        })
        token2 = login2.json()["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}

        # Создание комментария от user1
        resp = await ac.post("/comments/", json={
            "game_name": "Monopoly",
            "page": "1",
            "title": "My Review",
            "comment_text": "Great game!"
        }, headers=headers1)
        assert resp.status_code == 200
        comment1 = resp.json()
        assert comment1["user_id"] == user1_id
        assert comment1["username"] == "user1"
        assert comment1["game_name"] == "Monopoly"
        assert comment1["page"] == "1"
        assert comment1["title"] == "My Review"
        assert comment1["comment_text"] == "Great game!"
        comment1_id = comment1["id"]

        # Создание комментария от user2
        resp = await ac.post("/comments/", json={
            "game_name": "Monopoly",
            "page": "1",
            "title": "Agree",
            "comment_text": "I agree!"
        }, headers=headers2)
        assert resp.status_code == 200
        comment2 = resp.json()
        comment2_id = comment2["id"]

        # Получение комментариев
        resp = await ac.get("/comments/", params={"game_name": "Monopoly", "page": "1"})
        assert resp.status_code == 200
        comments = resp.json()
        assert len(comments) == 2
        # Проверить порядок по created_at
        assert comments[0]["username"] == "user1"
        assert comments[0]["comment_text"] == "Great game!"
        assert comments[1]["username"] == "user2"
        assert comments[1]["comment_text"] == "I agree!"


@pytest.mark.asyncio
async def test_update_own_comment(db_session, setup_clean_test_data):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Регистрация и логин
        reg = await ac.post("/auth/register", json={
            "username": "user3",
            "email": "user3@example.com",
            "password": "Test1234"
        })
        login = await ac.post("/auth/login", json={
            "username": "user3",
            "password": "Test1234"
        })
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Создание комментария
        resp = await ac.post("/comments/", json={
            "game_name": "Chess",
            "page": "rules",
            "title": "Initial Title",
            "comment_text": "Initial comment"
        }, headers=headers)
        comment = resp.json()
        comment_id = comment["id"]

        # Обновление комментария
        resp = await ac.put(f"/comments/{comment_id}", json={
            "title": "Updated Title",
            "comment_text": "Updated comment"
        }, headers=headers)
        assert resp.status_code == 200
        updated = resp.json()
        assert updated["title"] == "Updated Title"
        assert updated["comment_text"] == "Updated comment"
        assert updated["id"] == comment_id


@pytest.mark.asyncio
async def test_delete_own_comment(db_session, setup_clean_test_data):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Регистрация и логин
        reg = await ac.post("/auth/register", json={
            "username": "user4",
            "email": "user4@example.com",
            "password": "Test1234"
        })
        login = await ac.post("/auth/login", json={
            "username": "user4",
            "password": "Test1234"
        })
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Создание комментария
        resp = await ac.post("/comments/", json={
            "game_name": "Checkers",
            "page": "intro",
            "title": "Intro Review",
            "comment_text": "Nice intro"
        }, headers=headers)
        comment = resp.json()
        comment_id = comment["id"]

        # Удаление комментария
        resp = await ac.delete(f"/comments/{comment_id}", headers=headers)
        assert resp.status_code == 204

        # Проверка, что комментарий удален
        resp = await ac.get("/comments/", params={"game_name": "Checkers", "page": "intro"})
        assert resp.status_code == 200
        assert resp.json() == []


@pytest.mark.asyncio
async def test_update_other_comment_forbidden(db_session, setup_clean_test_data):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Регистрация и логин user5
        reg5 = await ac.post("/auth/register", json={
            "username": "user5",
            "email": "user5@example.com",
            "password": "Test1234"
        })
        login5 = await ac.post("/auth/login", json={
            "username": "user5",
            "password": "Test1234"
        })
        token5 = login5.json()["access_token"]
        headers5 = {"Authorization": f"Bearer {token5}"}

        # Регистрация и логин user6
        reg6 = await ac.post("/auth/register", json={
            "username": "user6",
            "email": "user6@example.com",
            "password": "Test1234"
        })
        login6 = await ac.post("/auth/login", json={
            "username": "user6",
            "password": "Test1234"
        })
        token6 = login6.json()["access_token"]
        headers6 = {"Authorization": f"Bearer {token6}"}

        # Создание комментария от user5
        resp = await ac.post("/comments/", json={
            "game_name": "Poker",
            "page": "rules",
            "title": "Poker Rules",
            "comment_text": "Poker rules"
        }, headers=headers5)
        comment = resp.json()
        comment_id = comment["id"]

        # Попытка обновить от user6
        resp = await ac.put(f"/comments/{comment_id}", json={
            "title": "Hacked",
            "comment_text": "Hacked"
        }, headers=headers6)
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_other_comment_forbidden(db_session, setup_clean_test_data):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Аналогично update, но для delete
        # Регистрация и логин user7
        reg7 = await ac.post("/auth/register", json={
            "username": "user7",
            "email": "user7@example.com",
            "password": "Test1234"
        })
        login7 = await ac.post("/auth/login", json={
            "username": "user7",
            "password": "Test1234"
        })
        token7 = login7.json()["access_token"]
        headers7 = {"Authorization": f"Bearer {token7}"}

        # Регистрация и логин user8
        reg8 = await ac.post("/auth/register", json={
            "username": "user8",
            "email": "user8@example.com",
            "password": "Test1234"
        })
        login8 = await ac.post("/auth/login", json={
            "username": "user8",
            "password": "Test1234"
        })
        token8 = login8.json()["access_token"]
        headers8 = {"Authorization": f"Bearer {token8}"}

        # Создание комментария от user7
        resp = await ac.post("/comments/", json={
            "game_name": "Bridge",
            "page": "basics",
            "title": "Bridge Basics",
            "comment_text": "Bridge basics"
        }, headers=headers7)
        comment = resp.json()
        comment_id = comment["id"]

        # Попытка удалить от user8
        resp = await ac.delete(f"/comments/{comment_id}", headers=headers8)
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_create_comment_validation(db_session, setup_clean_test_data):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Регистрация и логин
        reg = await ac.post("/auth/register", json={
            "username": "user9",
            "email": "user9@example.com",
            "password": "Test1234"
        })
        login = await ac.post("/auth/login", json={
            "username": "user9",
            "password": "Test1234"
        })
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Попытка создать комментарий с пустым текстом
        resp = await ac.post("/comments/", json={
            "game_name": "Test",
            "page": "1",
            "title": "Test Title",
            "comment_text": ""
        }, headers=headers)
        assert resp.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_create_comment_unauthorized(db_session, setup_clean_test_data):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Попытка создать комментарий без авторизации
        resp = await ac.post("/comments/", json={
            "game_name": "Test",
            "page": "1",
            "title": "Test",
            "comment_text": "Unauthorized comment"
        })
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_comment_unauthorized(db_session, setup_clean_test_data):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Регистрация и логин
        reg = await ac.post("/auth/register", json={
            "username": "user10",
            "email": "user10@example.com",
            "password": "Test1234"
        })
        login = await ac.post("/auth/login", json={
            "username": "user10",
            "password": "Test1234"
        })
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Создание комментария
        resp = await ac.post("/comments/", json={
            "game_name": "Test",
            "page": "1",
            "title": "Test",
            "comment_text": "Test comment"
        }, headers=headers)
        comment = resp.json()
        comment_id = comment["id"]

        # Попытка обновить без авторизации
        resp = await ac.put(f"/comments/{comment_id}", json={
            "title": "Updated",
            "comment_text": "Updated without auth"
        })
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_comment_unauthorized(db_session, setup_clean_test_data):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Регистрация и логин
        reg = await ac.post("/auth/register", json={
            "username": "user11",
            "email": "user11@example.com",
            "password": "Test1234"
        })
        login = await ac.post("/auth/login", json={
            "username": "user11",
            "password": "Test1234"
        })
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Создание комментария
        resp = await ac.post("/comments/", json={
            "game_name": "Test",
            "page": "1",
            "title": "Test",
            "comment_text": "Test comment"
        }, headers=headers)
        comment = resp.json()
        comment_id = comment["id"]

        # Попытка удалить без авторизации
        resp = await ac.delete(f"/comments/{comment_id}")
        assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_comment_not_found(db_session, setup_clean_test_data):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Регистрация и логин
        reg = await ac.post("/auth/register", json={
            "username": "user12",
            "email": "user12@example.com",
            "password": "Test1234"
        })
        login = await ac.post("/auth/login", json={
            "username": "user12",
            "password": "Test1234"
        })
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Попытка обновить несуществующий комментарий
        fake_id = str(uuid.uuid4())
        resp = await ac.put(f"/comments/{fake_id}", json={
            "title": "Updated",
            "comment_text": "Updated"
        }, headers=headers)
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_comment_not_found(db_session, setup_clean_test_data):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Регистрация и логин
        reg = await ac.post("/auth/register", json={
            "username": "user13",
            "email": "user13@example.com",
            "password": "Test1234"
        })
        login = await ac.post("/auth/login", json={
            "username": "user13",
            "password": "Test1234"
        })
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Попытка удалить несуществующий комментарий
        fake_id = str(uuid.uuid4())
        resp = await ac.delete(f"/comments/{fake_id}", headers=headers)
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_comment_empty_text(db_session, setup_clean_test_data):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Регистрация и логин
        reg = await ac.post("/auth/register", json={
            "username": "user14",
            "email": "user14@example.com",
            "password": "Test1234"
        })
        login = await ac.post("/auth/login", json={
            "username": "user14",
            "password": "Test1234"
        })
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Создание комментария
        resp = await ac.post("/comments/", json={
            "game_name": "Test",
            "page": "1",
            "title": "Initial",
            "comment_text": "Initial comment"
        }, headers=headers)
        comment = resp.json()
        comment_id = comment["id"]

        # Попытка обновить с пустым текстом
        resp = await ac.put(f"/comments/{comment_id}", json={
            "title": "Updated",
            "comment_text": ""
        }, headers=headers)
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_comment_long_text(db_session, setup_clean_test_data):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Регистрация и логин
        reg = await ac.post("/auth/register", json={
            "username": "user15",
            "email": "user15@example.com",
            "password": "Test1234"
        })
        login = await ac.post("/auth/login", json={
            "username": "user15",
            "password": "Test1234"
        })
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Попытка создать комментарий с текстом длиннее 1000 символов
        long_text = "a" * 1001
        resp = await ac.post("/comments/", json={
            "game_name": "Test",
            "page": "1",
            "title": "Test",
            "comment_text": long_text
        }, headers=headers)
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_comments_missing_game_name(db_session, setup_clean_test_data):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Попытка получить комментарии без game_name
        resp = await ac.get("/comments/", params={"page": "1"})
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_get_comments_missing_page(db_session, setup_clean_test_data):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Попытка получить комментарии без page
        resp = await ac.get("/comments/", params={"game_name": "Test"})
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_create_comment_missing_fields(db_session, setup_clean_test_data):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Регистрация и логин
        reg = await ac.post("/auth/register", json={
            "username": "user16",
            "email": "user16@example.com",
            "password": "Test1234"
        })
        login = await ac.post("/auth/login", json={
            "username": "user16",
            "password": "Test1234"
        })
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Попытка создать комментарий без game_name
        resp = await ac.post("/comments/", json={
            "page": "1",
            "title": "Test",
            "comment_text": "Test"
        }, headers=headers)
        assert resp.status_code == 422

        # Попытка создать комментарий без page
        resp = await ac.post("/comments/", json={
            "game_name": "Test",
            "title": "Test",
            "comment_text": "Test"
        }, headers=headers)
        assert resp.status_code == 422


@pytest.mark.asyncio
async def test_update_comment_invalid_id(db_session, setup_clean_test_data):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Регистрация и логин
        reg = await ac.post("/auth/register", json={
            "username": "user17",
            "email": "user17@example.com",
            "password": "Test1234"
        })
        login = await ac.post("/auth/login", json={
            "username": "user17",
            "password": "Test1234"
        })
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Попытка обновить с неправильным id
        resp = await ac.put("/comments/invalid-id", json={
            "title": "Updated",
            "comment_text": "Updated"
        }, headers=headers)
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_delete_comment_invalid_id(db_session, setup_clean_test_data):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Регистрация и логин
        reg = await ac.post("/auth/register", json={
            "username": "user18",
            "email": "user18@example.com",
            "password": "Test1234"
        })
        login = await ac.post("/auth/login", json={
            "username": "user18",
            "password": "Test1234"
        })
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Попытка удалить с неправильным id
        resp = await ac.delete("/comments/invalid-id", headers=headers)
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_multiple_comments_order(db_session, setup_clean_test_data):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Регистрация и логин пользователей
        reg1 = await ac.post("/auth/register", json={
            "username": "user19",
            "email": "user19@example.com",
            "password": "Test1234"
        })
        login1 = await ac.post("/auth/login", json={
            "username": "user19",
            "password": "Test1234"
        })
        token1 = login1.json()["access_token"]
        headers1 = {"Authorization": f"Bearer {token1}"}

        reg2 = await ac.post("/auth/register", json={
            "username": "user20",
            "email": "user20@example.com",
            "password": "Test1234"
        })
        login2 = await ac.post("/auth/login", json={
            "username": "user20",
            "password": "Test1234"
        })
        token2 = login2.json()["access_token"]
        headers2 = {"Authorization": f"Bearer {token2}"}

        # Создание нескольких комментариев
        resp1 = await ac.post("/comments/", json={
            "game_name": "OrderTest",
            "page": "page1",
            "title": "First",
            "comment_text": "First comment"
        }, headers=headers1)
        comment1 = resp1.json()

        resp2 = await ac.post("/comments/", json={
            "game_name": "OrderTest",
            "page": "page1",
            "title": "Second",
            "comment_text": "Second comment"
        }, headers=headers2)
        comment2 = resp2.json()

        resp3 = await ac.post("/comments/", json={
            "game_name": "OrderTest",
            "page": "page1",
            "title": "Third",
            "comment_text": "Third comment"
        }, headers=headers1)
        comment3 = resp3.json()

        # Получение комментариев
        resp = await ac.get("/comments/", params={"game_name": "OrderTest", "page": "page1"})
        assert resp.status_code == 200
        comments = resp.json()
        assert len(comments) == 3
        # Порядок по created_at
        assert comments[0]["comment_text"] == "First comment"
        assert comments[1]["comment_text"] == "Second comment"
        assert comments[2]["comment_text"] == "Third comment"


@pytest.mark.asyncio
async def test_comment_updated_at_changes(db_session, setup_clean_test_data):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # Регистрация и логин
        reg = await ac.post("/auth/register", json={
            "username": "user21",
            "email": "user21@example.com",
            "password": "Test1234"
        })
        login = await ac.post("/auth/login", json={
            "username": "user21",
            "password": "Test1234"
        })
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Создание комментария
        resp = await ac.post("/comments/", json={
            "game_name": "UpdateTest",
            "page": "page1",
            "title": "Initial",
            "comment_text": "Initial"
        }, headers=headers)
        comment = resp.json()
        comment_id = comment["id"]
        initial_updated_at = comment["updated_at"]

        # Обновление комментария
        resp = await ac.put(f"/comments/{comment_id}", json={
            "title": "Updated",
            "comment_text": "Updated"
        }, headers=headers)
        updated_comment = resp.json()
        assert updated_comment["updated_at"] != initial_updated_at

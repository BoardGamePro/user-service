import uuid
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPBearer
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from ..dependencies import get_db, get_current_user
from ..models import Comment, User
from ..schemas import CommentCreate, CommentOut, CommentUpdate

security = HTTPBearer()

comments = APIRouter(prefix="/comments", tags=["comments"])


@comments.get("/", response_model=List[CommentOut])
async def get_comments(
        game_name: str = Query(..., description="Название игры"),
        page: str = Query(..., description="Страница правил"),
        db: Annotated[AsyncSession, Depends(get_db)] = None
):
    """
    Возвращает список комментариев для указанной игры и страницы.
    """
    result = await db.execute(
        select(Comment, User.username).join(User, Comment.user_id == User.id).where(  # type: ignore
            and_(Comment.game_name == game_name, Comment.page == page)  # type: ignore
        ).order_by(Comment.created_at)
    )
    comment_rows = result.all()
    return [
        CommentOut(
            id=str(comment.id),
            user_id=str(comment.user_id),
            username=username,
            game_name=comment.game_name,
            page=comment.page,
            comment_text=comment.comment_text,
            created_at=comment.created_at.isoformat(),
            updated_at=comment.updated_at.isoformat(),
        )
        for comment, username in comment_rows
    ]


@comments.post("/", response_model=CommentOut, dependencies=[Depends(security)])
async def create_comment(
        data: CommentCreate,
        current: Annotated[User, Depends(get_current_user)],
        db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Создаёт новый комментарий от текущего пользователя.
    """
    new_comment = Comment(
        id=str(uuid.uuid4()),
        user_id=current.id,
        game_name=data.game_name,
        page=data.page,
        comment_text=data.comment_text,
    )
    db.add(new_comment)
    await db.commit()
    await db.refresh(new_comment)
    return CommentOut(
        id=str(new_comment.id),
        user_id=str(new_comment.user_id),
        username=current.username,  # type: ignore
        game_name=new_comment.game_name,
        page=new_comment.page,
        comment_text=new_comment.comment_text,
        created_at=new_comment.created_at.isoformat(),
        updated_at=new_comment.updated_at.isoformat(),
    )


@comments.put("/{comment_id}", response_model=CommentOut, dependencies=[Depends(security)])
async def update_comment(
        comment_id: str,
        data: CommentUpdate,
        current: Annotated[User, Depends(get_current_user)],
        db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Обновляет комментарий, если он принадлежит текущему пользователю.
    """
    result = await db.execute(select(Comment).where(Comment.id == comment_id))
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Комментарий не найден")
    if comment.user_id != current.id:  # type: ignore
        raise HTTPException(status_code=403, detail="Нет прав на изменение этого комментария")
    comment.comment_text = data.comment_text
    await db.commit()
    await db.refresh(comment)
    return CommentOut(
        id=str(comment.id),
        user_id=str(comment.user_id),
        username=current.username,  # type: ignore
        game_name=comment.game_name,
        page=comment.page,
        comment_text=comment.comment_text,
        created_at=comment.created_at.isoformat(),
        updated_at=comment.updated_at.isoformat(),
    )


@comments.delete("/{comment_id}", status_code=204, dependencies=[Depends(security)])
async def delete_comment(
        comment_id: str,
        current: Annotated[User, Depends(get_current_user)],
        db: Annotated[AsyncSession, Depends(get_db)]
):
    """
    Удаляет комментарий, если он принадлежит текущему пользователю.
    """
    result = await db.execute(select(Comment).where(Comment.id == comment_id))
    comment = result.scalar_one_or_none()
    if not comment:
        raise HTTPException(status_code=404, detail="Комментарий не найден")
    if comment.user_id != current.id:  # type: ignore
        raise HTTPException(status_code=403, detail="Нет прав на удаление этого комментария")
    await db.delete(comment)
    await db.commit()

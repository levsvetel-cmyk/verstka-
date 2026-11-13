import hashlib
from typing import Optional

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# берем из нашего файла database.py сессию и модели
# (при импорте файл сам создаст таблицы и добавит товары, если база пустая)
from database import Session, Product, User

app = FastAPI(title="Магазин техники Nexus")

# папка static - стили и картинки, папка templates - html страницы
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


# так товар будет выглядеть в ответе API
class ProductOut(BaseModel):
    id: int
    name: str
    price: float
    description: Optional[str] = None
    stock: int
    image: Optional[str] = None

    class Config:
        from_attributes = True


# превращаем пароль в набор символов (хэш), чтобы в базе не лежал настоящий пароль
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()


# главная страница. Если в адресе есть ?q=слово, показываем только подходящие товары
# registered приходит после успешной регистрации (/?registered=1)
@app.get("/")
def home(request: Request, q: Optional[str] = None, registered: Optional[str] = None):
    session = Session()
    products = session.query(Product).all()
    session.close()

    if q:
        # поиск по названию. Фильтруем в питоне, потому что SQLite
        # не умеет искать без учета регистра для русских букв
        products = [p for p in products if q.lower() in p.name.lower()]

    return templates.TemplateResponse(
        request, "index.html", {"products": products, "q": q, "registered": registered}
    )


# страница регистрации (просто показываем форму)
@app.get("/register")
def register_page(request: Request):
    return templates.TemplateResponse(request, "register.html", {})


# сюда приходят данные, когда пользователь нажал "Зарегистрироваться"
@app.post("/register")
def register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    password2: str = Form(...),
):
    username = username.strip()
    email = email.strip()

    # проверяем, что ввел пользователь
    error = None
    if len(username) < 3:
        error = "Логин должен быть не короче 3 символов"
    elif "@" not in email:
        error = "Введите правильную почту"
    elif len(password) < 6:
        error = "Пароль должен быть не короче 6 символов"
    elif password != password2:
        error = "Пароли не совпадают"

    session = Session()

    # проверяем, что такого логина еще нет в базе
    if error is None:
        old_user = session.query(User).filter_by(username=username).first()
        if old_user is not None:
            error = "Такой логин уже занят"

    # если есть ошибка - показываем форму снова, введенные данные оставляем
    if error:
        session.close()
        return templates.TemplateResponse(
            request,
            "register.html",
            {"error": error, "username": username, "email": email},
            status_code=400,
        )

    # ошибок нет - сохраняем нового пользователя
    user = User(username=username, email=email, password=hash_password(password))
    session.add(user)
    session.commit()
    session.close()

    # отправляем на главную с сообщением об успехе
    return RedirectResponse("/?registered=1", status_code=303)


# API: список всех товаров в json
@app.get("/api/products", response_model=list[ProductOut])
def get_products():
    session = Session()
    products = session.query(Product).all()
    session.close()
    return products


# API: один товар по id
@app.get("/api/products/{product_id}", response_model=ProductOut)
def get_product(product_id: int):
    session = Session()
    product = session.query(Product).filter(Product.id == product_id).first()
    session.close()

    if product is None:
        raise HTTPException(status_code=404, detail="Товар не найден")
    return product

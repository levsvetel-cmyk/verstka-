from datetime import datetime

from sqlalchemy import create_engine, Column, Integer, String, Float, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

# подключение к базе (файл shop.db создастся сам)
engine = create_engine("sqlite:///shop.db")
Base = declarative_base()


# пользователи (клиенты и админы)
class User(Base):
    __tablename__ = "auth_user"

    id = Column(Integer, primary_key=True)
    username = Column(String(50), unique=True, nullable=False)
    password = Column(String(128), nullable=False)
    email = Column(String(100))
    is_staff = Column(Boolean, default=False)

    orders = relationship("Order", back_populates="user")


# товары
class Product(Base):
    __tablename__ = "shop_product"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    price = Column(Float, nullable=False)
    description = Column(Text)
    stock = Column(Integer, default=0)
    image = Column(String(200))
    created_at = Column(DateTime, default=datetime.now)

    order_items = relationship("OrderItem", back_populates="product")


# заказы
class Order(Base):
    __tablename__ = "shop_order"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("auth_user.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.now)
    status = Column(String(30), default="new")
    total_price = Column(Float, default=0)

    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order")


# позиции в заказе
class OrderItem(Base):
    __tablename__ = "shop_orderitem"

    id = Column(Integer, primary_key=True)
    order_id = Column(Integer, ForeignKey("shop_order.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("shop_product.id"), nullable=False)
    quantity = Column(Integer, default=1)
    price = Column(Float, nullable=False)

    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")


# создаем все таблицы
Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)


# заполняем базу товарами с сайта (только если база пустая)
def add_start_data():
    session = Session()

    if session.query(Product).count() == 0:
        products = [
            Product(name="Смартфон Samsung 17A", price=24990, stock=10, image="img/phone.jpg"),
            Product(name="Ноутбук Asus Vivobok", price=49990, stock=5, image="img/laptop.jpg"),
            Product(name="Наушники AirPods 5", price=15490, stock=20, image="img/headphones.jpg"),
        ]
        session.add_all(products)

    if session.query(User).count() == 0:
        admin = User(username="admin", password="admin123", email="levsvetel@gmail.ru", is_staff=True)
        session.add(admin)

    session.commit()
    session.close()


add_start_data()


# проверка, что все работает
if __name__ == "__main__":
    session = Session()

    # создаем обычного пользователя, если его еще нет
    user = session.query(User).filter_by(username="ivan").first()
    if user is None:
        user = User(username="ivan", password="12345", email="ivan@mail.ru")
        session.add(user)
        session.commit()

    # делаем заказ: ноутбук и наушники
    laptop = session.query(Product).filter_by(name="Ноутбук Asus Vivobok").first()
    headphones = session.query(Product).filter_by(name="Наушники AirPods 5").first()

    order = Order(user_id=user.id, total_price=laptop.price + headphones.price)
    session.add(order)
    session.commit()

    session.add(OrderItem(order_id=order.id, product_id=laptop.id, quantity=1, price=laptop.price))
    session.add(OrderItem(order_id=order.id, product_id=headphones.id, quantity=1, price=headphones.price))
    session.commit()

    # выводим товары
    print("Товары:")
    for p in session.query(Product).all():
        print("  ", p.id, p.name, p.price, "руб., на складе:", p.stock)

    # выводим заказы
    print("Заказы:")
    for o in session.query(Order).all():
        print("  Заказ №", o.id, "пользователь:", o.user.username, "статус:", o.status, "сумма:", o.total_price)
        for i in o.items:
            print("     ", i.product.name, "x", i.quantity, "=", i.price)

    session.close()

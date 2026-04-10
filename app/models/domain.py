from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=True)
    password = Column(String(255), nullable=True)
    phone = Column(String(50), unique=True, index=True, nullable=True)
    github_id = Column(String(255), unique=True, index=True, nullable=True)
    avatar = Column(String(255), nullable=True)
    neighborhood = Column(String(100), nullable=True)  # 작성자 동네
    fcm_token = Column(String(500), nullable=True)  # FCM 토큰 추가
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    tokens = relationship("SMSToken", back_populates="user", cascade="all, delete-orphan")
    products = relationship("Product", back_populates="user", cascade="all, delete-orphan")
    posts = relationship("Post", back_populates="user", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="user", cascade="all, delete-orphan")
    likes = relationship("Like", back_populates="user", cascade="all, delete-orphan")
    product_favorites = relationship("ProductFavorite", back_populates="user", cascade="all, delete-orphan")
    messages = relationship("Message", back_populates="user")
    live_streams = relationship("LiveStream", back_populates="user")
    blocked_products = relationship(
        "ProductBlock",
        foreign_keys="ProductBlock.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
    )

class SMSToken(Base):
    __tablename__ = "sms_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    token = Column(String(255), unique=True, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user = relationship("User", back_populates="tokens")

class Product(Base):
    __tablename__ = "products"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    price = Column(Float, nullable=False)
    photo = Column(Text, nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(50), default="판매중")
    views = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user = relationship("User", back_populates="products")
    favorites = relationship("ProductFavorite", back_populates="product", cascade="all, delete-orphan")

    @property
    def neighborhood(self):
        return self.user.neighborhood if self.user else None

    @property
    def favorite_count(self):
        return len(self.favorites) if self.favorites else 0

class Post(Base):
    __tablename__ = "posts"
    
    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String(100), nullable=False)  # 게시글 주제: 동네친구, 맛집, 일반
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    views = Column(Integer, default=0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    user = relationship("User", back_populates="posts")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")
    likes = relationship("Like", back_populates="post", cascade="all, delete-orphan")
    images = relationship("PostImage", back_populates="post", cascade="all, delete-orphan")

class PostImage(Base):
    __tablename__ = "post_images"
    
    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(500), nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    post = relationship("Post", back_populates="images")

class Comment(Base):
    __tablename__ = "comments"
    
    id = Column(Integer, primary_key=True, index=True)
    payload = Column(Text, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), nullable=False)
    user = relationship("User", back_populates="comments")
    post = relationship("Post", back_populates="comments")

class Like(Base):
    __tablename__ = "likes"
    
    # Composite PK via columns
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    post_id = Column(Integer, ForeignKey("posts.id", ondelete="CASCADE"), primary_key=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    user = relationship("User", back_populates="likes")
    post = relationship("Post", back_populates="likes")

class ProductFavorite(Base):
    __tablename__ = "product_favorites"
    
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), primary_key=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="product_favorites")
    product = relationship("Product", back_populates="favorites")

class ChatRoom(Base):
    __tablename__ = "chat_rooms"
    
    id = Column(String(255), primary_key=True) # cuid mapped to string
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False)
    buyer_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    seller_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    buyer_left = Column(Boolean, default=False, server_default="0")
    seller_left = Column(Boolean, default=False, server_default="0")
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    product = relationship("Product", foreign_keys=[product_id])
    buyer = relationship("User", foreign_keys=[buyer_id])
    seller = relationship("User", foreign_keys=[seller_id])
    messages = relationship("Message", back_populates="room", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    payload = Column(Text, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    chat_room_id = Column(String(255), ForeignKey("chat_rooms.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    room = relationship("ChatRoom", back_populates="messages")
    user = relationship("User", back_populates="messages")

class LiveStream(Base):
    __tablename__ = "live_streams"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    stream_key = Column(String(255), nullable=False)
    stream_id = Column(String(255), nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", back_populates="live_streams")

class ProductBlock(Base):
    """상품 차단 테이블 - 유저가 특정 상품을 차단"""
    __tablename__ = "product_blocks"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", foreign_keys=[user_id], back_populates="blocked_products")
    product = relationship("Product", foreign_keys=[product_id])

class Report(Base):
    """신고 테이블 - 다형성 구조 (USER, PRODUCT, POST, COMMENT 등)"""
    __tablename__ = "reports"
    
    id = Column(Integer, primary_key=True, index=True)
    reporter_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    target_type = Column(String(50), nullable=False)   # USER, PRODUCT, POST, COMMENT
    target_id = Column(Integer, nullable=False)
    reason = Column(String(500), nullable=False)
    status = Column(String(50), default="PENDING")     # PENDING, RESOLVED
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    reporter = relationship("User", foreign_keys=[reporter_id])

from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Float
from sqlalchemy.orm import relationship
from .database import Base

class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    site_specific_id = Column(Integer)
    source = Column(String(255), index=True)
    date = Column(DateTime, index=True)
    review_text = Column(Text)
    rating = Column(Float, nullable=True)
    source_topic = Column(String(255), nullable=True)
    source_subtopic = Column(String(255), nullable=True)
    
    topics = relationship("ReviewTopicLink", back_populates="review")

class Topic(Base):
    __tablename__ = "topics"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), unique=True, index=True)
    description = Column(Text, nullable=True)

    reviews = relationship("ReviewTopicLink", back_populates="topic")

class ReviewTopicLink(Base):
    __tablename__ = "reviews_topics"

    id = Column(Integer, primary_key=True, index=True)
    review_id = Column(Integer, ForeignKey("reviews.id"))
    topic_id = Column(Integer, ForeignKey("topics.id"))
    sentiment = Column(String(50), index=True)

    review = relationship("Review", back_populates="topics")
    topic = relationship("Topic", back_populates="reviews")
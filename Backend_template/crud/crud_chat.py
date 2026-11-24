from sqlalchemy.ext.asyncio import AsyncSession
from config.db_config import get_database_session
from fastapi import  Depends
import  os
from sqlalchemy import select
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage , HumanMessage , AIMessage , ToolMessage
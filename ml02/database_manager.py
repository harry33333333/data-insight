# ml02/database_manager.py
import os
import glob
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

load_dotenv(dotenv_path=".env")

def get_engine():
    db_url = f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DATABASE')}"
    return create_engine(db_url)

def seed_database_from_local(data_dir="static/uploads"):
    """
    [独立辅助工具]：如果你想测试 AI 的 '无文件上传 -> 查数据库' 模式，
    可以先运行此脚本，将本地的 XLSX/CSV 灌入 PostgreSQL 中。
    """
    engine = get_engine()
    supported_extensions = ["*.csv", "*.xlsx", "*.xls"]
    data_files = []
    for ext in supported_extensions:
        data_files.extend(glob.glob(os.path.join(data_dir, ext)))
    
    if not data_files:
        print(f"⚠️ 在 {data_dir} 目录下没有找到任何文件。")
        return
    
    for file_path in data_files:
        base_name = os.path.basename(file_path)
        file_ext = base_name.split('.')[-1].lower()
        name_without_ext = base_name.rsplit('.', 1)[0]
        table_name = "user_behavior_" + "".join([c if c.isalnum() else "_" for c in name_without_ext]).strip("_")
        
        try:
            if file_ext == 'csv':
                df = pd.read_csv(file_path, encoding="utf-8", on_bad_lines="skip")
            elif file_ext in ['xlsx', 'xls']:
                df = pd.read_excel(file_path)
            
            df.to_sql(table_name, engine, if_exists="replace", index=False)
            print(f"✅ 成功将 {base_name} 灌入数据库表: {table_name}")
        except Exception as e:
            print(f"❌ 导入失败 {base_name}: {e}")

if __name__ == "__main__":
    print("开始数据库播种...")
    seed_database_from_local()
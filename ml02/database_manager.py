import os
import glob
import pandas as pd
from sqlalchemy import create_engine
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(dotenv_path=".env")

def get_engine():
    """构建 SQLAlchemy PostgreSQL 引擎"""
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    host = os.getenv("POSTGRES_HOST")
    port = os.getenv("POSTGRES_PORT")
    db = os.getenv("POSTGRES_DATABASE")
    
    # 构造连接字符串
    db_url = f"postgresql://{user}:{password}@{host}:{port}/{db}"
    return create_engine(db_url)

def import_csvs_to_postgres(data_dir="data"):
    """
    扫描 data 目录下的所有 CSV 和 Excel 文件，并自动推导格式导入 PostgreSQL
    (保持函数名不变以兼容 app.py)
    """
    engine = get_engine()
    
    # 自动扫描目录下支持的所有文件格式
    supported_extensions = ["*.csv", "*.xlsx", "*.xls"]
    data_files = []
    for ext in supported_extensions:
        data_files.extend(glob.glob(os.path.join(data_dir, ext)))
    
    if not data_files:
        return {"status": "error", "message": f"在 {data_dir} 目录下没有找到任何 CSV 或 Excel 文件！请先放入数据文件。"}
    
    imported_tables = []
    
    for file_path in data_files:
        # 提取文件名和后缀
        base_name = os.path.basename(file_path)
        file_ext = base_name.split('.')[-1].lower()
        name_without_ext = base_name.rsplit('.', 1)[0]
        
        # 清理表名中的特殊字符，确保 SQL 兼容（比如替换掉中划线和空格）
        table_name = "user_behavior_" + "".join([c if c.isalnum() else "_" for c in name_without_ext]).strip("_")
        
        try:
            # 💡 核心升级：根据文件后缀智能路由读取方式
            if file_ext == 'csv':
                df = pd.read_csv(file_path, encoding="utf-8", on_bad_lines="skip")
            elif file_ext in ['xlsx', 'xls']:
                # 读取 Excel 文件（支持多 sheet 中的第一个 sheet，也可自定义）
                df = pd.read_excel(file_path)
            else:
                continue
            
            # 将 DataFrame 导入 PostgreSQL（如果表存在则覆盖）
            df.to_sql(table_name, engine, if_exists="replace", index=False)
            imported_tables.append(table_name)
            print(f"✅ 成功导入表: {table_name} (格式: {file_ext.upper()}, 行数: {len(df)})")
        except Exception as e:
            print(f"❌ 导入文件 {file_path} 失败: {e}")
            
    return {
        "status": "success", 
        "message": f"成功将 {len(imported_tables)} 个文件 (CSV/Excel) 导入 PostgreSQL 成为业务表！", 
        "tables": imported_tables
    }

if __name__ == "__main__":
    import_csvs_to_postgres()
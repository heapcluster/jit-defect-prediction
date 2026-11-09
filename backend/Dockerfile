# 后端运行时镜像（依赖版本单一权威 = data_model/environment.yml；build context = 仓库根）
FROM python:3.12-slim

WORKDIR /app

# torch 为 PyPI CPU 版（容器无 GPU）；GPU 训练不在此镜像
RUN pip install --no-cache-dir \
    torch==2.5.1 \
    pandas==3.0.5 numpy==2.5.3 scikit-learn==1.9.1 scipy==1.18.1 \
    xgboost==3.4.1 lightgbm==4.6.0 pytorch-tabnet==4.1.0 \
    joblib==1.6.0 shap==0.52.0 \
    fastapi==0.141.1 uvicorn==0.53.0 sqlalchemy==2.0.54 pymysql==1.2.3 python-dotenv==1.2.3

# 后端代码 + 特征抽取器脚本（data_model/preparation 纯 stdlib，随镜像走）
COPY backend/ /app/backend/
COPY data_model/preparation/ /app/data_model/preparation/

WORKDIR /app/backend
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

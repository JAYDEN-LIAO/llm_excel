import os
from minio import Minio
from minio.error import S3Error

# 配置信息（与你的 docker/.env 保持一致）
MINIO_ENDPOINT = "127.0.0.1:9000"
MINIO_ACCESS_KEY = "llmexcel"
MINIO_SECRET_KEY = "llmexcel"
BUCKET_NAME = "llm-excel" # 如果你的存储桶名字不同，请修改这里

def fix_bucket_policy():
    client = Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=False
    )

    try:
        # 1. 检查桶是否存在
        if not client.bucket_exists(BUCKET_NAME):
            print(f"Creating bucket: {BUCKET_NAME}")
            client.make_bucket(BUCKET_NAME)
        
        # 2. 定义公开读取策略
        # 这个策略允许任何人读取该桶内的文件，修复预览和下载问题
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": ["*"]},
                    "Action": ["s3:GetBucketLocation", "s3:ListBucket"],
                    "Resource": [f"arn:aws:s3:::{BUCKET_NAME}"],
                },
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": ["*"]},
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{BUCKET_NAME}/*"],
                },
            ],
        }

        import json
        client.set_bucket_policy(BUCKET_NAME, json.dumps(policy))
        print(f"✅ 成功！存储桶 '{BUCKET_NAME}' 的权限已设为公开读取。")
        
    except S3Error as e:
        print(f"❌ 发生错误: {e}")

if __name__ == "__main__":
    fix_bucket_policy()
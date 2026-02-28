import json
from minio import Minio

# 1. 连接到你的本地 MinIO
client = Minio(
    "localhost:9000",
    access_key="minioadmin",
    secret_key="minioadmin",
    secure=False
)

bucket_name = "llmexcel"

# 2. 编写公开访问的策略 (允许所有人下载文件)
policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {"AWS": "*"},
            "Action": "s3:GetObject",
            "Resource": f"arn:aws:s3:::{bucket_name}/*"
        }
    ]
}

# 3. 将策略应用到桶上
try:
    client.set_bucket_policy(bucket_name, json.dumps(policy))
    print(f"✅ 太棒了！成功将 MinIO 桶 '{bucket_name}' 的权限设置为公开下载！")
except Exception as e:
    print(f"❌ 设置失败，错误信息: {e}")
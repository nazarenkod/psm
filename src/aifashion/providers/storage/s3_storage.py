"""Адаптер S3-совместимого хранилища (MinIO / R2 / S3). Реализует StorageProvider.

boto3 синхронный — оборачиваем вызовы в ``asyncio.to_thread``, чтобы не блокировать
event loop бота.
"""
from __future__ import annotations

import asyncio

import boto3


class S3Storage:
    def __init__(
        self,
        *,
        endpoint_url: str,
        bucket: str,
        access_key: str,
        secret_key: str,
        region: str = "us-east-1",
    ) -> None:
        self._bucket = bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
        )

    async def put(self, key: str, data: bytes, content_type: str) -> str:
        await asyncio.to_thread(
            self._client.put_object,
            Bucket=self._bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        return key

    async def delete_prefix(self, prefix: str) -> int:
        def _delete() -> int:
            paginator = self._client.get_paginator("list_objects_v2")
            count = 0
            for page in paginator.paginate(Bucket=self._bucket, Prefix=prefix):
                objs = [{"Key": o["Key"]} for o in page.get("Contents", [])]
                if objs:
                    self._client.delete_objects(Bucket=self._bucket, Delete={"Objects": objs})
                    count += len(objs)
            return count

        return await asyncio.to_thread(_delete)

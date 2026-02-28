"""多文件关联处理接口"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.core.database import AsyncSessionLocal
from app.engine.models import (
    JoinOperation, MergeOperation, CrossFileReferenceOperation,
    JoinCondition, FileCollection
)
from app.engine.excel_parser import ExcelParser
from app.engine.executor import Executor
from app.models.user import User
from app.models.file import File
from app.schemas.response import ApiResponse
from app.services.excel import get_files_by_ids_from_db, load_tables_from_files
from sqlalchemy import select

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/multifile", tags=["多文件关联"])


# ============ Request Models ============


class JoinConditionRequest(BaseModel):
    """连接条件请求"""
    left_column: str = Field(..., description="左表列名")
    right_column: str = Field(..., description="右表列名")
    operator: str = Field("=", description="比较运算符: =, >, <, >=, <=, <>")


class JoinRequest(BaseModel):
    """表连接请求"""
    left_file_id: str = Field(..., description="左文件ID")
    left_table: str = Field(..., description="左表名")
    right_file_id: str = Field(..., description="右文件ID")
    right_table: str = Field(..., description="右表名")
    join_type: str = Field("inner", description="连接类型: inner, left, right, full")
    conditions: List[JoinConditionRequest] = Field(..., description="连接条件列表")
    output_sheet_name: str = Field("连接结果", description="输出表名")


class MergeRequest(BaseModel):
    """数据合并请求"""
    file_ids: List[str] = Field(..., description="文件ID列表")
    tables: List[str] = Field(..., description="对应的表名列表")
    merge_type: str = Field("vertical", description="合并类型: vertical(垂直), horizontal(水平)")
    output_sheet_name: str = Field("合并结果", description="输出表名")


class CrossReferenceRequest(BaseModel):
    """跨文件引用请求"""
    source_file_id: str = Field(..., description="源文件ID")
    source_table: str = Field(..., description="源表名")
    source_column: str = Field(..., description="源列名")
    target_file_id: str = Field(..., description="目标文件ID")
    target_table: str = Field(..., description="目标表名")
    target_column: str = Field(..., description="目标列名（新列或现有列）")
    reference_type: str = Field("copy", description="引用类型: copy(复制), formula(公式)")
    output_sheet_name: Optional[str] = Field(None, description="输出表名（如为None则在原表修改）")


class MultiFileAnalysisRequest(BaseModel):
    """多文件分析请求"""
    file_ids: List[str] = Field(..., description="文件ID列表")
    analysis_type: str = Field("schema", description="分析类型: schema(结构), relationships(关系), stats(统计)")


# ============ Response Models ============


class JoinResult(BaseModel):
    """连接结果"""
    success: bool
    output_file_id: Optional[str] = None
    output_sheet_name: Optional[str] = None
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    error: Optional[str] = None


class MergeResult(BaseModel):
    """合并结果"""
    success: bool
    output_file_id: Optional[str] = None
    output_sheet_name: Optional[str] = None
    row_count: Optional[int] = None
    column_count: Optional[int] = None
    error: Optional[str] = None


class CrossReferenceResult(BaseModel):
    """跨文件引用结果"""
    success: bool
    target_file_id: Optional[str] = None
    target_sheet_name: Optional[str] = None
    target_column: Optional[str] = None
    formula: Optional[str] = None
    error: Optional[str] = None


class FileSchema(BaseModel):
    """文件结构信息"""
    file_id: str
    filename: str
    sheets: Dict[str, List[str]]  # sheet名 -> 列名列表


class RelationshipInfo(BaseModel):
    """文件关系信息"""
    source_file: str
    source_sheet: str
    source_column: str
    target_file: str
    target_sheet: str
    target_column: str
    relationship_type: str  # "potential_join", "same_schema", "data_overlap"


class MultiFileAnalysisResult(BaseModel):
    """多文件分析结果"""
    file_schemas: List[FileSchema]
    relationships: List[RelationshipInfo]
    suggestions: List[str]


# ============ Helper Functions ============


async def validate_files_access(file_ids: List[UUID], user_id: UUID, db: AsyncSession) -> List[File]:
    """验证用户对文件的访问权限"""
    files = await get_files_by_ids_from_db(file_ids, db)
    
    # 检查文件是否存在且属于当前用户
    valid_files = []
    for file in files:
        if str(file.user_id) != str(user_id):
            raise HTTPException(
                status_code=403,
                detail=f"无权访问文件: {file.filename}"
            )
        valid_files.append(file)
    
    return valid_files


async def load_file_collection(file_ids: List[str], user_id: UUID, db: AsyncSession) -> FileCollection:
    """加载文件集合"""
    try:
        uuid_file_ids = [UUID(fid) for fid in file_ids]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"无效的 file_id 格式: {e}")
    
    files = await validate_files_access(uuid_file_ids, user_id, db)
    return load_tables_from_files(files)


# ============ API Endpoints ============


@router.post("/analyze", response_model=ApiResponse[MultiFileAnalysisResult])
async def analyze_multifile(
    request: MultiFileAnalysisRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    分析多个文件的结构和关系
    
    返回文件结构、潜在关联关系和处理建议
    """
    try:
        # 加载文件集合
        file_collection = await load_file_collection(request.file_ids, current_user.id, db)
        
        # 获取文件结构
        file_schemas = []
        schemas = file_collection.get_schemas()
        
        for file_id, file_schema in schemas.items():
            # 获取文件名
            file = file_collection.get_file(file_id)
            sheet_columns = {}
            
            for sheet_name, columns in file_schema.items():
                # 转换列格式：从 {"A": "列名1", "B": "列名2"} 到 ["列名1", "列名2"]
                column_names = list(columns.values())
                sheet_columns[sheet_name] = column_names
            
            file_schemas.append(FileSchema(
                file_id=file_id,
                filename=file.filename,
                sheets=sheet_columns
            ))
        
        # 分析潜在关系（简化版：查找相同列名）
        relationships = []
        suggestions = []
        
        file_ids = list(schemas.keys())
        for i, file_id1 in enumerate(file_ids):
            for file_id2 in file_ids[i+1:]:
                file1 = file_collection.get_file(file_id1)
                file2 = file_collection.get_file(file_id2)
                
                for sheet1 in file1.get_sheet_names():
                    for sheet2 in file2.get_sheet_names():
                        table1 = file1.get_sheet(sheet1)
                        table2 = file2.get_sheet(sheet2)
                        
                        cols1 = set(table1.get_columns())
                        cols2 = set(table2.get_columns())
                        common_cols = cols1.intersection(cols2)
                        
                        for col in common_cols:
                            relationships.append(RelationshipInfo(
                                source_file=file_id1,
                                source_sheet=sheet1,
                                source_column=col,
                                target_file=file_id2,
                                target_sheet=sheet2,
                                target_column=col,
                                relationship_type="potential_join"
                            ))
                
                # 添加建议
                suggestions.append(f"文件 '{file1.filename}' 和 '{file2.filename}' 可以通过共同列名进行关联")
        
        if not relationships:
            suggestions.append("未发现明显的关联列，建议手动指定连接条件")
        
        result = MultiFileAnalysisResult(
            file_schemas=file_schemas,
            relationships=relationships,
            suggestions=suggestions
        )
        
        return ApiResponse(data=result)
        
    except Exception as e:
        logger.error(f"多文件分析失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@router.post("/join", response_model=ApiResponse[JoinResult])
async def join_files(
    request: JoinRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    执行表连接操作
    
    支持内连接、左连接、右连接、全外连接
    """
    try:
        # 加载文件集合
        file_ids = [request.left_file_id, request.right_file_id]
        file_collection = await load_file_collection(file_ids, current_user.id, db)
        
        # 创建连接条件
        join_conditions = [
            JoinCondition(
                left_column=cond.left_column,
                right_column=cond.right_column,
                operator=cond.operator
            )
            for cond in request.conditions
        ]
        
        # 创建连接操作
        join_op = JoinOperation(
            left_file_id=request.left_file_id,
            left_table=request.left_table,
            right_file_id=request.right_file_id,
            right_table=request.right_table,
            join_type=request.join_type,
            conditions=join_conditions,
            output={"type": "new_sheet", "name": request.output_sheet_name},
            description=f"{request.join_type}连接 {request.left_file_id}.{request.left_table} 和 {request.right_file_id}.{request.right_table}"
        )
        
        # 执行连接操作
        executor = Executor(file_collection)
        result = executor.execute([join_op])
        
        if result.has_errors():
            error_msg = "; ".join(result.errors)
            return ApiResponse(
                code=400,
                data=JoinResult(success=False, error=error_msg),
                msg="连接操作失败"
            )
        
        # 获取结果
        output_file_id = request.left_file_id  # 默认输出到左文件
        output_sheet_name = request.output_sheet_name
        
        # 获取结果数据
        if output_file_id in result.new_sheets and output_sheet_name in result.new_sheets[output_file_id]:
            result_data = result.new_sheets[output_file_id][output_sheet_name]
            row_count = len(result_data)
            column_count = len(result_data.columns) if hasattr(result_data, 'columns') else 0
        else:
            row_count = 0
            column_count = 0
        
        join_result = JoinResult(
            success=True,
            output_file_id=output_file_id,
            output_sheet_name=output_sheet_name,
            row_count=row_count,
            column_count=column_count
        )
        
        return ApiResponse(data=join_result)
        
    except Exception as e:
        logger.error(f"文件连接失败: {e}", exc_info=True)
        return ApiResponse(
            code=500,
            data=JoinResult(success=False, error=str(e)),
            msg="连接操作失败"
        )


@router.post("/merge", response_model=ApiResponse[MergeResult])
async def merge_files(
    request: MergeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    执行数据合并操作
    
    支持垂直合并（追加行）和水平合并（追加列）
    """
    try:
        # 验证参数
        if len(request.file_ids) != len(request.tables):
            return ApiResponse(
                code=400,
                data=MergeResult(success=False, error="file_ids 和 tables 长度必须相同"),
                msg="参数错误"
            )
        
        if len(request.file_ids) < 2:
            return ApiResponse(
                code=400,
                data=MergeResult(success=False, error="至少需要2个文件进行合并"),
                msg="参数错误"
            )
        
        # 加载文件集合
        file_collection = await load_file_collection(request.file_ids, current_user.id, db)
        
        # 创建合并操作
        merge_op = MergeOperation(
            file_ids=request.file_ids,
            tables=request.tables,
            merge_type=request.merge_type,
            output={"type": "new_sheet", "name": request.output_sheet_name},
            description=f"{request.merge_type}合并 {len(request.file_ids)} 个文件"
        )
        
        # 执行合并操作
        executor = Executor(file_collection)
        result = executor.execute([merge_op])
        
        if result.has_errors():
            error_msg = "; ".join(result.errors)
            return ApiResponse(
                code=400,
                data=MergeResult(success=False, error=error_msg),
                msg="合并操作失败"
            )
        
        # 获取结果（默认输出到第一个文件）
        output_file_id = request.file_ids[0]
        output_sheet_name = request.output_sheet_name
        
        # 获取结果数据
        if output_file_id in result.new_sheets and output_sheet_name in result.new_sheets[output_file_id]:
            result_data = result.new_sheets[output_file_id][output_sheet_name]
            row_count = len(result_data)
            column_count = len(result_data.columns) if hasattr(result_data, 'columns') else 0
        else:
            row_count = 0
            column_count = 0
        
        merge_result = MergeResult(
            success=True,
            output_file_id=output_file_id,
            output_sheet_name=output_sheet_name,
            row_count=row_count,
            column_count=column_count
        )
        
        return ApiResponse(data=merge_result)
        
    except Exception as e:
        logger.error(f"文件合并失败: {e}", exc_info=True)
        return ApiResponse(
            code=500,
            data=MergeResult(success=False, error=str(e)),
            msg="合并操作失败"
        )


@router.post("/reference", response_model=ApiResponse[CrossReferenceResult])
async def cross_file_reference(
    request: CrossReferenceRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    执行跨文件引用操作
    
    支持复制数据或生成公式引用
    """
    try:
        # 加载文件集合
        file_ids = [request.source_file_id, request.target_file_id]
        file_collection = await load_file_collection(file_ids, current_user.id, db)
        
        # 创建跨文件引用操作
        output_type = "in_place"
        if request.output_sheet_name:
            output_type = {"type": "new_sheet", "name": request.output_sheet_name}
        
        reference_op = CrossFileReferenceOperation(
            source_file_id=request.source_file_id,
            source_table=request.source_table,
            source_column=request.source_column,
            target_file_id=request.target_file_id,
            target_table=request.target_table,
            target_column=request.target_column,
            reference_type=request.reference_type,
            output=output_type,
            description=f"从 {request.source_file_id}.{request.source_table} 引用 {request.source_column} 到 {request.target_file_id}.{request.target_table}"
        )
        
        # 执行引用操作
        executor = Executor(file_collection)
        result = executor.execute([reference_op])
        
        if result.has_errors():
            error_msg = "; ".join(result.errors)
            return ApiResponse(
                code=400,
                data=CrossReferenceResult(success=False, error=error_msg),
                msg="引用操作失败"
            )
        
        # 获取公式（如果适用）
        formula = None
        if request.reference_type == "formula" and result.excel_formulas:
            formula = result.excel_formulas[0]
        
        reference_result = CrossReferenceResult(
            success=True,
            target_file_id=request.target_file_id,
            target_sheet_name=request.target_table,
            target_column=request.target_column,
            formula=formula
        )
        
        return ApiResponse(data=reference_result)
        
    except Exception as e:
        logger.error(f"跨文件引用失败: {e}", exc_info=True)
        return ApiResponse(
            code=500,
            data=CrossReferenceResult(success=False, error=str(e)),
            msg="引用操作失败"
        )
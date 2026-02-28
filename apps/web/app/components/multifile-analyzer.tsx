import { useState, useEffect } from 'react'
import { Loader2, Link, ChevronRight, AlertCircle } from 'lucide-react'

interface FileSchema {
  file_id: string
  filename: string
  sheets: Record<string, string[]>
}

interface RelationshipInfo {
  source_file: string
  source_sheet: string
  source_column: string
  target_file: string
  target_sheet: string
  target_column: string
  relationship_type: string
}

interface MultiFileAnalysisResult {
  file_schemas: FileSchema[]
  relationships: RelationshipInfo[]
  suggestions: string[]
}

interface MultiFileAnalyzerProps {
  fileIds: string[]
  onAnalysisComplete?: (result: MultiFileAnalysisResult) => void
  onJoinRequest?: (joinConfig: {
    leftFileId: string
    leftTable: string
    rightFileId: string
    rightTable: string
    joinType: string
    conditions: Array<{ left_column: string; right_column: string; operator: string }>
  }) => void
}

const MultiFileAnalyzer = ({
  fileIds,
  onAnalysisComplete,
  onJoinRequest
}: MultiFileAnalyzerProps) => {
  const [loading, setLoading] = useState(false)
  const [analysisResult, setAnalysisResult] = useState<MultiFileAnalysisResult | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [joinConfig, setJoinConfig] = useState({
    leftFileId: '',
    leftTable: '',
    rightFileId: '',
    rightTable: '',
    joinType: 'inner' as 'inner' | 'left' | 'right' | 'full',
    conditions: [{ left_column: '', right_column: '', operator: '=' }]
  })

  // 分析多文件
  const analyzeFiles = async () => {
    if (fileIds.length < 2) {
      setError('请选择至少2个文件进行分析')
      return
    }

    setLoading(true)
    setError(null)

    try {
      const response = await fetch('/api/multifile/analyze', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          file_ids: fileIds,
          analysis_type: 'schema'
        })
      })

      const data = await response.json()
      
      if (data.code === 200 && data.data) {
        const result = data.data
        setAnalysisResult(result)
        onAnalysisComplete?.(result)
        
        // 初始化选择
        if (result.file_schemas.length >= 2) {
          setJoinConfig({
            leftFileId: result.file_schemas[0].file_id,
            leftTable: Object.keys(result.file_schemas[0].sheets)[0] || '',
            rightFileId: result.file_schemas[1].file_id,
            rightTable: Object.keys(result.file_schemas[1].sheets)[0] || '',
            joinType: 'inner',
            conditions: [{ left_column: '', right_column: '', operator: '=' }]
          })
        }
      } else {
        setError(data.msg || '分析失败')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '分析请求失败')
    } finally {
      setLoading(false)
    }
  }

  // 执行连接操作
  const handleJoin = () => {
    if (!joinConfig.leftFileId || !joinConfig.rightFileId) {
      setError('请选择左右文件')
      return
    }

    if (!joinConfig.conditions.every(cond => cond.left_column && cond.right_column)) {
      setError('请填写完整的连接条件')
      return
    }

    onJoinRequest?.(joinConfig)
  }

  // 获取文件的sheet列表
  const getFileSheets = (fileId: string) => {
    const file = analysisResult?.file_schemas.find(f => f.file_id === fileId)
    return file ? Object.keys(file.sheets) : []
  }

  // 获取sheet的列列表
  const getSheetColumns = (fileId: string, sheetName: string) => {
    const file = analysisResult?.file_schemas.find(f => f.file_id === fileId)
    return file?.sheets[sheetName] || []
  }

  useEffect(() => {
    if (fileIds.length >= 2) {
      analyzeFiles()
    }
  }, [fileIds])

  if (fileIds.length < 2) {
    return (
      <div className="p-4 border rounded bg-yellow-50 border-yellow-200">
        <div className="flex items-center">
          <AlertCircle className="h-4 w-4 mr-2 text-yellow-600" />
          <span className="text-sm text-yellow-800">请选择至少2个文件进行多文件关联分析</span>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      {/* 分析状态 */}
      <div className="border rounded">
        <div className="p-4 border-b">
          <div className="flex items-center gap-2">
            <Link className="h-5 w-5" />
            <h3 className="font-medium">多文件关联分析</h3>
          </div>
          <p className="text-sm text-gray-500 mt-1">
            分析 {fileIds.length} 个文件的结构和关联关系
          </p>
        </div>
        
        <div className="p-4">
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
              <span className="ml-2">正在分析文件结构...</span>
            </div>
          ) : error ? (
            <div className="p-3 bg-red-50 border border-red-200 rounded">
              <div className="flex items-center">
                <AlertCircle className="h-4 w-4 mr-2 text-red-600" />
                <span className="text-sm text-red-800">{error}</span>
              </div>
            </div>
          ) : analysisResult ? (
            <div className="space-y-4">
              {/* 文件结构概览 */}
              <div>
                <h4 className="text-sm font-medium mb-2">文件结构</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  {analysisResult.file_schemas.map(file => (
                    <div key={file.file_id} className="border rounded p-3">
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="font-medium text-sm">{file.filename}</p>
                          <p className="text-xs text-gray-500">
                            {Object.keys(file.sheets).length} 个表, {Object.values(file.sheets).flat().length} 列
                          </p>
                        </div>
                      </div>
                      <div className="mt-2 space-y-1">
                        {Object.entries(file.sheets).map(([sheetName, columns]) => (
                          <div key={sheetName} className="text-xs">
                            <span className="font-medium">{sheetName}:</span>
                            <span className="text-gray-500 ml-1">
                              {columns.slice(0, 3).join(', ')}
                              {columns.length > 3 && `...等 ${columns.length} 列`}
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* 关联关系和建议 */}
              {analysisResult.relationships.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium mb-2">发现关联关系</h4>
                  <div className="space-y-2">
                    {analysisResult.relationships.map((rel, index) => (
                      <div key={index} className="flex items-center text-sm p-2 bg-gray-50 rounded">
                        <Link className="h-3 w-3 mr-2" />
                        <span className="font-medium">{rel.source_file}.{rel.source_sheet}.{rel.source_column}</span>
                        <ChevronRight className="h-3 w-3 mx-2" />
                        <span className="font-medium">{rel.target_file}.{rel.target_sheet}.{rel.target_column}</span>
                        <span className="ml-2 px-2 py-0.5 text-xs border rounded">
                          {rel.relationship_type === 'potential_join' ? '可连接' : '关联'}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {analysisResult.suggestions.length > 0 && (
                <div className="p-3 bg-blue-50 border border-blue-200 rounded">
                  <div className="flex items-center">
                    <AlertCircle className="h-4 w-4 mr-2 text-blue-600" />
                    <span className="font-medium text-sm">处理建议</span>
                  </div>
                  <ul className="list-disc pl-4 mt-2 space-y-1">
                    {analysisResult.suggestions.map((suggestion, index) => (
                      <li key={index} className="text-sm text-blue-800">{suggestion}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ) : (
            <button 
              onClick={analyzeFiles} 
              disabled={loading}
              className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            >
              {loading && <Loader2 className="inline mr-2 h-4 w-4 animate-spin" />}
              开始分析
            </button>
          )}
        </div>
      </div>

      {/* 表连接配置 */}
      {analysisResult && (
        <div className="border rounded">
          <div className="p-4 border-b">
            <h4 className="font-medium">表连接配置</h4>
            <p className="text-sm text-gray-500 mt-1">
              将两个表中的数据根据指定条件连接起来
            </p>
          </div>
          
          <div className="p-4 space-y-4">
            <div className="grid grid-cols-2 gap-4">
              {/* 左表选择 */}
              <div className="space-y-2">
                <label className="text-sm font-medium">左表</label>
                <div className="space-y-2">
                  <select
                    className="w-full p-2 border rounded"
                    value={joinConfig.leftFileId}
                    onChange={(e) => setJoinConfig({ ...joinConfig, leftFileId: e.target.value })}
                  >
                    <option value="">选择文件</option>
                    {analysisResult.file_schemas.map(file => (
                      <option key={file.file_id} value={file.file_id}>
                        {file.filename}
                      </option>
                    ))}
                  </select>
                  {joinConfig.leftFileId && (
                    <select
                      className="w-full p-2 border rounded"
                      value={joinConfig.leftTable}
                      onChange={(e) => setJoinConfig({ ...joinConfig, leftTable: e.target.value })}
                    >
                      <option value="">选择表</option>
                      {getFileSheets(joinConfig.leftFileId).map(sheet => (
                        <option key={sheet} value={sheet}>{sheet}</option>
                      ))}
                    </select>
                  )}
                </div>
              </div>

              {/* 右表选择 */}
              <div className="space-y-2">
                <label className="text-sm font-medium">右表</label>
                <div className="space-y-2">
                  <select
                    className="w-full p-2 border rounded"
                    value={joinConfig.rightFileId}
                    onChange={(e) => setJoinConfig({ ...joinConfig, rightFileId: e.target.value })}
                  >
                    <option value="">选择文件</option>
                    {analysisResult.file_schemas.map(file => (
                      <option key={file.file_id} value={file.file_id}>
                        {file.filename}
                      </option>
                    ))}
                  </select>
                  {joinConfig.rightFileId && (
                    <select
                      className="w-full p-2 border rounded"
                      value={joinConfig.rightTable}
                      onChange={(e) => setJoinConfig({ ...joinConfig, rightTable: e.target.value })}
                    >
                      <option value="">选择表</option>
                      {getFileSheets(joinConfig.rightFileId).map(sheet => (
                        <option key={sheet} value={sheet}>{sheet}</option>
                      ))}
                    </select>
                  )}
                </div>
              </div>
            </div>

            {/* 连接类型 */}
            <div className="space-y-2">
              <label className="text-sm font-medium">连接类型</label>
              <div className="flex gap-2">
                {['inner', 'left', 'right', 'full'].map(type => (
                  <button
                    key={type}
                    type="button"
                    className={`px-3 py-1 text-sm rounded ${joinConfig.joinType === type ? 'bg-blue-600 text-white' : 'bg-gray-100 text-gray-800'}`}
                    onClick={() => setJoinConfig({ ...joinConfig, joinType: type as any })}
                  >
                    {type === 'inner' && '内连接'}
                    {type === 'left' && '左连接'}
                    {type === 'right' && '右连接'}
                    {type === 'full' && '全连接'}
                  </button>
                ))}
              </div>
            </div>

            {/* 连接条件 */}
            <div className="space-y-2">
              <label className="text-sm font-medium">连接条件</label>
              {joinConfig.conditions.map((condition, index) => (
                <div key={index} className="flex items-center gap-2">
                  <select
                    className="flex-1 p-2 border rounded"
                    value={condition.left_column}
                    onChange={(e) => {
                      const newConditions = [...joinConfig.conditions]
                      newConditions[index] = { ...newConditions[index], left_column: e.target.value }
                      setJoinConfig({ ...joinConfig, conditions: newConditions })
                    }}
                    disabled={!joinConfig.leftFileId || !joinConfig.leftTable}
                  >
                    <option value="">选择左表列</option>
                    {joinConfig.leftFileId && joinConfig.leftTable && 
                      getSheetColumns(joinConfig.leftFileId, joinConfig.leftTable).map(col => (
                        <option key={col} value={col}>{col}</option>
                      ))
                    }
                  </select>
                  <select
                    className="w-20 p-2 border rounded"
                    value={condition.operator}
                    onChange={(e) => {
                      const newConditions = [...joinConfig.conditions]
                      newConditions[index] = { ...newConditions[index], operator: e.target.value as any }
                      setJoinConfig({ ...joinConfig, conditions: newConditions })
                    }}
                  >
                    <option value="=">=</option>
                    <option value="gt">大于</option>
                    <option value="lt">小于</option>
                    <option value="gte">大于等于</option>
                    <option value="lte">小于等于</option>
                    <option value="neq">不等于</option>
                  </select>
                  <select
                    className="flex-1 p-2 border rounded"
                    value={condition.right_column}
                    onChange={(e) => {
                      const newConditions = [...joinConfig.conditions]
                      newConditions[index] = { ...newConditions[index], right_column: e.target.value }
                      setJoinConfig({ ...joinConfig, conditions: newConditions })
                    }}
                    disabled={!joinConfig.rightFileId || !joinConfig.rightTable}
                  >
                    <option value="">选择右表列</option>
                    {joinConfig.rightFileId && joinConfig.rightTable && 
                      getSheetColumns(joinConfig.rightFileId, joinConfig.rightTable).map(col => (
                        <option key={col} value={col}>{col}</option>
                      ))
                    }
                  </select>
                </div>
              ))}
            </div>

            {/* 操作按钮 */}
            <div className="flex justify-end">
              <button
                onClick={handleJoin}
                className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"
              >
                执行连接
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default MultiFileAnalyzer
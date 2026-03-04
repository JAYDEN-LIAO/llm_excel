Url：
测试环境http://maasapp.aip.bj.bob.test:8080/apis/ais/qwen3-32b?body_format=openai

请求方式：POST
Header参数：
名称 值
Content-Type application/json
Authorization MaaS提供API KEY

Query 参数：

query 值 是否必须
body_format openai 是

接口参数

参数 是否必填 格式 含义 备注
model 必填 String 模型名 固定为 qwen3
message 必填 List[Object] 传入模型的信息
role 必填 String 角色 user/system/assistant等
content 必填 String 输入问题内容
max_tokens 非必填 Int 生成输出的最大token数 模型启动配置8192
stream 非必填 bolean 是否流式输出 默认非流式
top_p 非必填 float 核采样 默认0.8，0-1之间
temperature
非必填 float 温度采样 默认0.8，0-1之间 值越高随机性与多样性越强

接口参数示例

{
"model": "qwen3",
"messages": [
{
"role": "user",
"content": "你是谁"
}
]
}

返回参数
参数 格式 含义 备注
model String 模型名 固定为 qwen3
choices List[Object] 模型输出 一个问题对应一个输出
index String 索引
message
Object 模型生成信息
role String 模型返回角色
content String 模型输出内容
tool_calls String 工具调用
finish_reason
String 停止原因
usage
Int 使用量 Token计算使用量
prompt_tokens
Int 输入prompt的token数
completion_tokens
Int 生成token数
total_tokens
Int 输入+输出总token数

{
"id": "endpoint_common_6",
"object": "chat.completion",
"created": 1746600616,
"model": "qwen3",
"choices": [
{
"index": 0,
"message": {
"role": "assistant",
"tool_calls": null,
"content": "<think>\n嗯，用户问“你是谁”，我需要先确认他们想知道什么。可能他们刚接触我，或者想确认我的身份。首先，我应该介绍自己的名字，Qwen，然后说明我是通义实验室研发的大模型。接下来，要突出我的功能，比如回答问题、创作文字、编程等，这样用户知道我能帮他们做什么。还要提到多语言支持，这样国际用户会觉得方便。另外，强调对话理解能力，说明我能处理复杂或长对话，这样用户会觉得交流顺畅。最后，保持友好，邀请用户提问，这样能促进进一步的互动。要注意用简洁明了的语言，避免技术术语，让用户容易理解。可能用户有更深层的需求，比如寻找特定功能或解决某个问题，所以结尾的邀请很重要，让他们知道可以进一步交流。检查有没有遗漏的重要信息，比如训练数据截止时间，但用户没问，可能暂时不用提。保持回答自然，不生硬，让对话感觉亲切。\n</think>\n\n你好！我是Qwen，是通义实验室研发的超大规模语言模型。我可以帮助你回答问题、创作文字、编程、表达观点，甚至玩游戏。我支持多种语言，包括但不限于中文、英文、德语、法语、西班牙语等，能够处理各种复杂的对话场景。如果你有任何问题或需要帮助，随时告诉我，我会尽力为你提供支持！"
},
"logprobs": null,
"finish_reason": "stop"
}
],
"usage": {
"prompt_tokens": 10,
"completion_tokens": 284,
"total_tokens": 294
},
"prefill_time": 52,
"decode_time_arr": [
33,
32,
32,
32,
32,
32,
32,
32,
32,
32,
32,
32,
32,
32,
32,
32,
32,
32,
32,
32,
32,
32
]
}

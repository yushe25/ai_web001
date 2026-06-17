import os
import json
import re
import logging
from typing import Dict, Optional
import requests
from openai import OpenAI
from local_ai import RAGFlowClient

# 配置日志记录
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ResumeAnalyzer:
    """AI 简历分析器"""

    def __init__(self, backend_type: str = 'qwen', ragflow_api_key: Optional[str] = None,
                 ragflow_base_url: Optional[str] = None):
        self.backend_type = backend_type.lower()

        # Qwen 配置
        self.qwen_api_key = os.getenv('QWEN_API_KEY', 'sk-d4fbbcca0a1d4af986d746a659b977cc')
        self.qwen_model = os.getenv('QWEN_MODEL', 'qwen-turbo')

        # RAGFlow 配置
        self.ragflow_api_key = ragflow_api_key or os.getenv('RAGFLOW_API_KEY',
                                                            'ragflow-Y2NzYyNmRjNjAyMzExZjFhY2I1ODJmNG')
        self.ragflow_base_url = ragflow_base_url or os.getenv('RAGFLOW_BASE_URL', 'http://localhost:9380/api/v1')

        if self.backend_type not in ['qwen', 'local']:
            logger.warning(f"不支持的后端类型: {self.backend_type}，将使用默认的 qwen 后端")
            self.backend_type = 'qwen'

        logger.info(f"简历分析器初始化完成，使用后端: {self.backend_type}")

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """从 PDF 文件中提取文本"""
        import PyPDF2

        full_text = ""
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text = page.extract_text()
                if text:
                    full_text += text + "\n"

        return full_text.strip()

    def extract_text_from_docx(self, docx_path: str) -> str:
        """从 Word 文档中提取文本"""
        from docx import Document

        doc = Document(docx_path)
        full_text = []
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                full_text.append(paragraph.text.strip())

        return "\n".join(full_text)

    def extract_text_from_file(self, file_path: str) -> str:
        """根据文件扩展名自动选择提取方法"""
        ext = os.path.splitext(file_path)[1].lower()

        if ext == '.pdf':
            return self.extract_text_from_pdf(file_path)
        elif ext in ['.docx', '.doc']:
            return self.extract_text_from_docx(file_path)
        else:
            raise ValueError(f"不支持的文件格式: {ext}")

    def _call_qwen_api(self, job_description: str, resume_text: str) -> Dict:
        """调用阿里云 Qwen API 进行分析"""
        try:
            client = OpenAI(
                api_key=self.qwen_api_key,
                base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
            )

            prompt = f"""请对以下简历与职位描述进行匹配度分析，并严格按照 JSON 格式返回结果。

【职位描述】
{job_description}

【简历内容】
{resume_text}

请按照以下 JSON 格式返回分析结果（不要包含其他文字）：
{{
  "match_score": 85,
  "matched_skills": ["技能1", "技能2"],
  "missing_skills": ["技能3"],
  "summary": "简短评价"
}}

注意：
1. match_score 必须是 0-100 的整数
2. matched_skills 和 missing_skills 必须是字符串数组
3. summary 要简洁明了"""

            response = client.chat.completions.create(
                model=self.qwen_model,
                messages=[
                    {"role": "system",
                     "content": "你是一个专业的简历分析专家，请直接返回严格的JSON格式数据，不要包含任何Markdown标记（如```json）或多余的解释文字。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )

            result_text = response.choices[0].message.content
            result = json.loads(result_text)

            logger.info(f"Qwen API 简历分析成功，匹配度: {result.get('match_score', 0)}")
            return result

        except Exception as e:
            logger.error(f"Qwen API 调用失败: {str(e)}")
            raise

    def _call_local_ai(self, job_description: str, resume_text: str) -> Dict:
        """调用本地 RAGFlow/Ollama API 进行分析"""
        try:
            client = RAGFlowClient(
                api_key=self.ragflow_api_key,
                base_url=self.ragflow_base_url
            )

            client.init_chat()

            prompt = f"""请对以下简历与职位描述进行匹配度分析，并严格按照 JSON 格式返回结果。

【职位描述】
{job_description}

【简历内容】
{resume_text}

请按照以下 JSON 格式返回分析结果（不要包含其他文字）：
{{
  "match_score": 85,
  "matched_skills": ["技能1", "技能2"],
  "missing_skills": ["技能3"],
  "summary": "简短评价"
}}

注意：
1. match_score 必须是 0-100 的整数
2. matched_skills 和 missing_skills 必须是字符串数组
3. summary 要简洁明了"""

            answer = client.ask(prompt)

            if not answer:
                raise Exception("本地 AI 返回为空")

            # 尝试从回答中提取 JSON
            result_text = answer

            # 优化后的正则表达式，用于提取 Markdown 代码块中的 JSON
            json_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
            match = re.search(json_pattern, answer, re.DOTALL)
            if match:
                result_text = match.group(1)

            result = json.loads(result_text)

            # 验证返回数据的结构
            required_keys = ['match_score', 'matched_skills', 'missing_skills', 'summary']
            if not all(key in result for key in required_keys):
                raise Exception("本地 AI 返回的数据结构不完整")

            logger.info(f"Local AI 简历分析成功，匹配度: {result.get('match_score', 0)}")
            return result

        except Exception as e:
            logger.error(f"Local AI 调用失败: {str(e)}")
            raise

    def analyze_resume(self, job_description: str, resume_file_path: str) -> Dict:
        """分析简历与职位的匹配度"""
        try:
            resume_text = self.extract_text_from_file(resume_file_path)

            if self.backend_type == 'qwen':
                result = self._call_qwen_api(job_description, resume_text)
            elif self.backend_type == 'local':
                result = self._call_local_ai(job_description, resume_text)
            else:
                raise ValueError(f"不支持的后端类型: {self.backend_type}")

            return result

        except Exception as e:
            logger.error(f"简历分析失败: {str(e)}")
            return {
                'match_score': 0,
                'matched_skills': [],
                'missing_skills': [],
                'summary': f'分析失败: {str(e)}'
            }


# # 创建默认分析器实例
# analyzer = ResumeAnalyzer()
#
#
# def analyze_resume(job_description: str, resume_file_path: str) -> Dict:
#     """便捷函数 - 分析简历与职位的匹配度"""
#     return analyzer.analyze_resume(job_description, resume_file_path)
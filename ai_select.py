import os
import json
import logging
from typing import Dict

import requests
from openai import OpenAI

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class ResumeAnalyzer:
    """AI 简历分析器"""

    def __init__(self):
        self.qwen_api_key = 'sk-b5f6e81d2147495aa41990f201182f29'
        self.qwen_model = 'qwen-turbo'

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

    def analyze_resume(self, job_description: str, resume_file_path: str) -> Dict:
        """分析简历与职位的匹配度"""
        try:
            resume_text = self.extract_text_from_file(resume_file_path)

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
                    {"role": "system", "content": "你是一个专业的简历分析专家，请直接返回严格的JSON格式数据，不要包含任何Markdown标记（如```json）或多余的解释文字。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )

            result_text = response.choices[0].message.content
            result = json.loads(result_text)

            logger.info(f"简历分析成功，匹配度: {result['match_score']}")
            return result

        except Exception as e:
            logger.error(f"简历分析失败: {str(e)}")
            return {
                'match_score': 0,
                'matched_skills': [],
                'missing_skills': [],
                'summary': f'分析失败: {str(e)}'
            }


analyzer = ResumeAnalyzer()


def analyze_resume(job_description: str, resume_file_path: str) -> Dict:
    """便捷函数 - 分析简历与职位的匹配度"""
    return analyzer.analyze_resume(job_description, resume_file_path)

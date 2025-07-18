import PyPDF2
import re
import os
import shutil
from datetime import datetime
import logging

class PDFProcessor:
    def __init__(self):
        self.processed_receipts = set()
        self.current_output_dir = '收货单库'
        self.setup_logging()
        self.load_processed_receipts()
    
    def setup_logging(self):
        # 创建logs目录
        if not os.path.exists('logs'):
            os.makedirs('logs')
        
        # 设置日志文件名，包含时间戳
        log_filename = os.path.join('logs', f'pdf_processor_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
        
        # 配置日志记录器
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filename, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
    
    def log_info(self, message):
        print(message)  # 保持控制台输出
        logging.info(message)  # 写入日志文件
    
    def log_error(self, message):
        print(f'错误: {message}')  # 保持控制台输出
        logging.error(message)  # 写入日志文件
    
    def load_processed_receipts(self):
        try:
            if os.path.exists('processed.txt'):
                with open('processed.txt', 'r', encoding='utf-8') as f:
                    self.processed_receipts = set(line.strip() for line in f)
                self.log_info(f'已加载 {len(self.processed_receipts)} 个已处理的收货单号')
        except Exception as e:
            self.log_error(f'加载已处理收货单号时出错: {str(e)}')
    
    def save_processed_receipts(self, new_receipts):
        try:
            # 先读取现有的收货单号
            existing_receipts = set()
            if os.path.exists('processed.txt'):
                with open('processed.txt', 'r', encoding='utf-8') as f:
                    existing_receipts = set(line.strip() for line in f)
            
            # 追加新的收货单号
            with open('processed.txt', 'a', encoding='utf-8') as f:
                for receipt in new_receipts:
                    if receipt not in existing_receipts:
                        f.write(receipt + '\n')
                        self.processed_receipts.add(receipt)
                        self.log_info(f'添加新的收货单号: {receipt}')
        except Exception as e:
            self.log_error(f'保存收货单号时出错: {str(e)}')
    
    def save_pages_to_file(self, vendor, receipt, pages, base_dir, rev_date):
        if receipt in self.processed_receipts:
            self.log_info(f'跳过已处理的收货单号: {receipt}')
            return receipt  # 修改：返回跳过的收货单号
            
        safe_vendor_name = re.sub(r'[<>:"/\\|?*]', '_', vendor)
        # 创建供应商目录
        vendor_dir = os.path.join(base_dir, safe_vendor_name)
        # 创建日期目录
        date_dir = os.path.join(vendor_dir, rev_date) if rev_date else vendor_dir
        
        if not os.path.exists(vendor_dir):
            os.makedirs(vendor_dir)
        if not os.path.exists(date_dir):
            os.makedirs(date_dir)
            
        output_path = os.path.join(date_dir, f'{receipt}.pdf')
        writer = PyPDF2.PdfWriter()
        
        for page in pages:
            writer.add_page(page)
            
        with open(output_path, 'wb') as output_file:
            writer.write(output_file)
            
        self.log_info(f'已创建文件: {output_path}')
    
    def process_pdfs(self):
        try:
            # 创建输出目录
            if not os.path.exists(self.current_output_dir):
                os.makedirs(self.current_output_dir)
                self.log_info(f'创建输出目录: {self.current_output_dir}')
            
            # 创建归档目录
            archive_dir = 'archive'
            if not os.path.exists(archive_dir):
                os.makedirs(archive_dir)
                self.log_info(f'创建归档目录: {archive_dir}')
            
            # 获取当前目录下的所有PDF文件
            pdf_files = [f for f in os.listdir('.') if f.endswith('.pdf')]
            if not pdf_files:
                self.log_info('当前目录下没有找到PDF文件')
                return
            
            total_files = len(pdf_files)
            total_pages = 0
            total_vendors = set()
            new_receipts = set()
            skipped_receipts = set()  # 新增：用于记录跳过的收货单号
            
            # 处理每个PDF文件
            for file_index, pdf_name in enumerate(pdf_files, 1):
                pdf_path = os.path.join('.', pdf_name)
                self.log_info(f'\n开始处理PDF文件: {pdf_path}')
                
                with open(pdf_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    file_pages = len(reader.pages)
                    total_pages += file_pages
                    self.log_info(f'PDF文件页数: {file_pages}')
                    
                    # 遍历每一页
                    current_receipt = None
                    current_vendor = None
                    page_buffer = []
                    
                    for page_num in range(file_pages):
                        # 获取当前页面
                        page = reader.pages[page_num]
                        text = page.extract_text()
                        
                        # 提取收货单号
                        receipt_match = re.search(r'收货单号\s*RF:\s*(RFAH7970\d+)', text)
                        new_receipt = receipt_match.group(1) if receipt_match else None
                        
                        # 提取收货日期
                        rev_date_match = re.search(r'收货日期\s*Rev\. Date:\s*(\d{4}-\d{2}-\d{2})', text)
                        new_rev_date = rev_date_match.group(1) if rev_date_match else None
                        
                        # 使用多个正则表达式模式查找供应商信息
                        patterns = [
                            r'供应商[/\\]?Vendor[：:](.*?)\n',
                            r'供应商[/\\]?Vendor[：:](.*?)\s',
                            r'供应商名称[：:](.*?)\n',
                            r'供应商名称[：:](.*?)\s',
                            r'VENDOR[：:](.*?)\n',
                            r'VENDOR[：:](.*?)\s'
                        ]
                        
                        new_vendor = None
                        for pattern in patterns:
                            vendor_match = re.search(pattern, text, re.IGNORECASE)
                            if vendor_match:
                                vendor = vendor_match.group(1).strip()
                                if vendor:
                                    new_vendor = vendor
                                    total_vendors.add(vendor)
                                    break
                        
                        # 如果找到新的收货单号或供应商，保存当前缓存的页面
                        if (new_receipt and new_receipt != current_receipt) or (new_vendor and new_vendor != current_vendor):
                            if current_vendor and current_receipt and page_buffer:
                                skipped = self.save_pages_to_file(current_vendor, current_receipt, page_buffer, self.current_output_dir, new_rev_date)
                                if skipped:
                                    skipped_receipts.add(skipped)
                                else:
                                    new_receipts.add(current_receipt)
                                page_buffer = []
                            
                            current_receipt = new_receipt or current_receipt
                            current_vendor = new_vendor or current_vendor
                            current_rev_date = new_rev_date  # 保存当前收货日期
                        
                        # 将当前页面添加到缓存
                        if current_vendor and current_receipt:
                            page_buffer.append(page)
                    
                    # 保存最后一组页面
                    if current_vendor and current_receipt and page_buffer:
                        skipped = self.save_pages_to_file(current_vendor, current_receipt, page_buffer, self.current_output_dir, current_rev_date)
                        if skipped:
                            skipped_receipts.add(skipped)
                        else:
                            new_receipts.add(current_receipt)
                
                # 将处理完的文件移动到归档目录
                archive_path = os.path.join(archive_dir, os.path.basename(pdf_path))
                shutil.move(pdf_path, archive_path)
                self.log_info(f'已将文件归档: {archive_path}')
            
            # 保存新的收货单号
            if new_receipts:
                self.save_processed_receipts(new_receipts)
                self.log_info(f'\n已保存 {len(new_receipts)} 个新的收货单号到 processed.txt')
            
            self.log_info(f'\n处理完成！共处理 {total_files} 个文件，{total_pages} 页，涉及 {len(total_vendors)} 个供应商。')
            self.log_info(f'新增 {len(new_receipts)} 个收货单号，跳过 {len(skipped_receipts)} 个已处理的收货单号。')
        
        except Exception as e:
            self.log_error(str(e))

def main():
    processor = PDFProcessor()
    processor.process_pdfs()

if __name__ == '__main__':
    main()
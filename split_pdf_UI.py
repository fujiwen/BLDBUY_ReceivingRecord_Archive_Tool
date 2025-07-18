import PyPDF2
import re
import os
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from threading import Thread
from datetime import datetime

class PDFSplitterApp:
    def __init__(self, root):
        self.root = root
        self.root.title('PDF供应商拆分工具')
        self.root.geometry('800x600')
        
        # 设置样式
        style = ttk.Style()
        style.configure('TButton', padding=5)
        style.configure('TLabel', padding=5)
        style.configure('TProgressbar', thickness=20)
        
        # 创建主框架
        main_frame = ttk.Frame(root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 文件选择区域
        self.file_frame = ttk.LabelFrame(main_frame, text='文件选择', padding=10)
        self.file_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        self.files_listbox = tk.Listbox(self.file_frame, width=70, height=5)
        self.files_listbox.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        files_scrollbar = ttk.Scrollbar(self.file_frame, orient=tk.VERTICAL, command=self.files_listbox.yview)
        files_scrollbar.grid(row=0, column=2, sticky=(tk.N, tk.S))
        self.files_listbox.configure(yscrollcommand=files_scrollbar.set)
        
        self.browse_button = ttk.Button(self.file_frame, text='添加文件...', command=self.browse_files)
        self.browse_button.grid(row=1, column=0, padx=5)
        
        self.clear_button = ttk.Button(self.file_frame, text='清除文件', command=self.clear_files)
        self.clear_button.grid(row=1, column=1, padx=5)
        
        # 进度显示区域
        self.progress_frame = ttk.LabelFrame(main_frame, text='处理进度', padding=10)
        self.progress_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.progress_frame, length=600, mode='determinate', variable=self.progress_var)
        self.progress_bar.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=5, pady=5)
        
        self.status_var = tk.StringVar(value='就绪')
        self.status_label = ttk.Label(self.progress_frame, textvariable=self.status_var)
        self.status_label.grid(row=1, column=0, sticky=tk.W, padx=5)
        
        # 结果显示区域
        self.result_frame = ttk.LabelFrame(main_frame, text='处理结果', padding=10)
        self.result_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        self.result_text = tk.Text(self.result_frame, height=15, width=70)
        self.result_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        scrollbar = ttk.Scrollbar(self.result_frame, orient=tk.VERTICAL, command=self.result_text.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.result_text.configure(yscrollcommand=scrollbar.set)
        
        # 控制按钮
        self.button_frame = ttk.Frame(main_frame)
        self.button_frame.grid(row=3, column=0, sticky=(tk.E), padx=5, pady=5)
        
        self.start_button = ttk.Button(self.button_frame, text='开始处理', command=self.start_processing)
        self.start_button.grid(row=0, column=0, padx=5)
        
        self.clear_log_button = ttk.Button(self.button_frame, text='清除日志', command=self.clear_results)
        self.clear_log_button.grid(row=0, column=1, padx=5)
        
        # 配置grid权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        self.result_frame.columnconfigure(0, weight=1)
        self.result_frame.rowconfigure(0, weight=1)
        
        # 存储选择的文件路径
        self.selected_files = []
        # 存储已处理的收货单号
        self.processed_receipts = set()
        # 存储当前输出目录
        self.current_output_dir = None
    
    def load_processed_receipts(self):
        try:
            if os.path.exists('processed.txt'):
                with open('processed.txt', 'r', encoding='utf-8') as f:
                    self.processed_receipts = set(line.strip() for line in f)
                self.log_message(f'已加载 {len(self.processed_receipts)} 个已处理的收货单号')
        except Exception as e:
            self.log_message(f'加载已处理收货单号时出错: {str(e)}')
    
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
                        self.log_message(f'添加新的收货单号: {receipt}')
        except Exception as e:
            self.log_message(f'保存收货单号时出错: {str(e)}')
    
    def browse_files(self):
        filenames = filedialog.askopenfilenames(filetypes=[("PDF文件", "*.pdf")])
        if filenames:
            for filename in filenames:
                if filename not in self.selected_files:
                    self.selected_files.append(filename)
                    self.files_listbox.insert(tk.END, filename)
            # 在选择文件后加载收货单号
            self.load_processed_receipts()
    
    def clear_files(self):
        self.selected_files = []
        self.files_listbox.delete(0, tk.END)
        self.processed_receipts.clear()
    
    def clear_results(self):
        self.result_text.delete(1.0, tk.END)
        self.progress_var.set(0)
        self.status_var.set('就绪')
    
    def log_message(self, message):
        self.result_text.insert(tk.END, message + '\n')
        self.result_text.see(tk.END)
    
    def cleanup_temp_files(self):
        # 已禁用自动清理功能
        pass
    
    def start_processing(self):
        if not self.selected_files:
            messagebox.showerror('错误', '请先选择PDF文件！')
            return
        
        self.start_button.state(['disabled'])
        self.clear_log_button.state(['disabled'])
        self.browse_button.state(['disabled'])
        self.clear_button.state(['disabled'])
        self.progress_var.set(0)
        self.result_text.delete(1.0, tk.END)
        
        # 在新线程中处理PDF
        Thread(target=self.process_pdfs, daemon=True).start()
    
    def save_pages_to_file(self, vendor, receipt, pages, base_dir):
        if receipt in self.processed_receipts:
            self.log_message(f'跳过已处理的收货单号: {receipt}')
            return
            
        safe_vendor_name = re.sub(r'[<>:"/\\|?*]', '_', vendor)
        vendor_dir = os.path.join(base_dir, safe_vendor_name)
        
        if not os.path.exists(vendor_dir):
            os.makedirs(vendor_dir)
            
        output_path = os.path.join(vendor_dir, f'{receipt}.pdf')
        writer = PyPDF2.PdfWriter()
        
        for page in pages:
            writer.add_page(page)
            
        with open(output_path, 'wb') as output_file:
            writer.write(output_file)
            
        self.log_message(f'已创建文件: {output_path}')
    
    def process_pdfs(self):
        try:
            # 创建输出目录
            self.current_output_dir = '收货单库'
            if not os.path.exists(self.current_output_dir):
                os.makedirs(self.current_output_dir)
                self.log_message(f'创建输出目录: {self.current_output_dir}')
            
            # 创建归档目录
            archive_dir = 'archive'
            if not os.path.exists(archive_dir):
                os.makedirs(archive_dir)
                self.log_message(f'创建归档目录: {archive_dir}')
            
            total_files = len(self.selected_files)
            total_pages = 0
            total_vendors = set()
            new_receipts = set()
            
            # 处理每个PDF文件
            for file_index, pdf_path in enumerate(self.selected_files, 1):
                self.status_var.set(f'正在处理文件 {file_index}/{total_files}: {os.path.basename(pdf_path)}')
                self.log_message(f'\n开始处理PDF文件: {pdf_path}')
                
                with open(pdf_path, 'rb') as file:
                    reader = PyPDF2.PdfReader(file)
                    file_pages = len(reader.pages)
                    total_pages += file_pages
                    self.log_message(f'PDF文件页数: {file_pages}')
                    
                    # 遍历每一页
                    current_receipt = None
                    current_vendor = None
                    page_buffer = []
                    
                    for page_num in range(file_pages):
                        self.progress_var.set((file_index - 1 + (page_num + 1) / file_pages) / total_files * 100)
                        
                        # 获取当前页面
                        page = reader.pages[page_num]
                        text = page.extract_text()
                        
                        # 提取收货单号
                        receipt_match = re.search(r'收货单号\s*RF:\s*(RFAH7970\d+)', text)
                        new_receipt = receipt_match.group(1) if receipt_match else None
                        
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
                                self.save_pages_to_file(current_vendor, current_receipt, page_buffer, self.current_output_dir)
                                new_receipts.add(current_receipt)
                                page_buffer = []
                            
                            current_receipt = new_receipt or current_receipt
                            current_vendor = new_vendor or current_vendor
                        
                        # 将当前页面添加到缓存
                        if current_vendor and current_receipt:
                            page_buffer.append(page)
                    
                    # 保存最后一组页面
                    if current_vendor and current_receipt and page_buffer:
                        self.save_pages_to_file(current_vendor, current_receipt, page_buffer, self.current_output_dir)
                        new_receipts.add(current_receipt)
                
                # 将处理完的文件移动到归档目录
                archive_path = os.path.join(archive_dir, os.path.basename(pdf_path))
                shutil.move(pdf_path, archive_path)
                self.log_message(f'已将文件归档: {archive_path}')
            
            # 保存新的收货单号
            if new_receipts:
                self.save_processed_receipts(new_receipts)
                self.log_message(f'\n已保存 {len(new_receipts)} 个新的收货单号到 processed.txt')
            
            # 清理临时文件
            self.cleanup_temp_files()
            
            self.status_var.set('处理完成！')
            messagebox.showinfo('完成', f'PDF文件处理完成！\n共处理 {total_files} 个文件，{total_pages} 页，涉及 {len(total_vendors)} 个供应商。\n新增 {len(new_receipts)} 个收货单号。')
        
        except Exception as e:
            self.log_message(f'错误: {str(e)}')
            messagebox.showerror('错误', f'处理PDF文件时发生错误：\n{str(e)}')
            self.status_var.set('处理出错')
        
        finally:
            self.start_button.state(['!disabled'])
            self.clear_log_button.state(['!disabled'])
            self.browse_button.state(['!disabled'])
            self.clear_button.state(['!disabled'])

def main():
    root = tk.Tk()
    app = PDFSplitterApp(root)
    root.mainloop()

if __name__ == '__main__':
    main()
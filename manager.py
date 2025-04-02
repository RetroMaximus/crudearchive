import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
try:
    from crudearch.archive_handler import CrudeArchiveHandler
except ImportError:
    try:
        from archive_handler import CrudeArchiveHandler
    except ImportError:
        try:
            from .archive_handler import CrudeArchiveHandler
        except ImportError as e:
            raise ImportError(
                "Failed to import CrudeArchiveHandler. "
                "Tried:\n"
                "1. crudearch.archive_handler\n"
                "2. archive_handler\n"
                "3. .archive_handler\n"
                f"Original error: {str(e)}\n"
            )

class CrudeArchiveManager:
    """GUI application for managing CRUD archives"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("CRUD Archive Manager")
        self.root.geometry("800x600")
        
        self.archive_handler = None
        self.current_file = None
        
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the user interface"""
        # Menu bar
        menubar = tk.Menu(self.root)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="New Archive", command=self.new_archive)
        file_menu.add_command(label="Open Archive", command=self.open_archive)
        file_menu.add_command(label="Save Archive", command=self.save_archive)
        file_menu.add_command(label="Save Archive As", command=self.save_archive_as)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)
        
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Add File", command=self.add_file_dialog)
        edit_menu.add_command(label="Remove File", command=self.remove_file)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        
        self.root.config(menu=menubar)
        
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # File list
        file_list_frame = ttk.Labelframe(main_frame, text="Archive Contents")
        file_list_frame.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        self.file_list = ttk.Treeview(file_list_frame, columns=('type'), selectmode='browse')
        self.file_list.heading('#0', text='Filename')
        self.file_list.heading('type', text='Type')
        self.file_list.column('#0', width=300)
        self.file_list.column('type', width=100)
        self.file_list.pack(fill=tk.BOTH, expand=True)
        
        self.file_list.bind('<<TreeviewSelect>>', self.on_file_select)
        
        # File preview
        preview_frame = ttk.Labelframe(main_frame, text="File Preview")
        preview_frame.pack(fill=tk.BOTH, expand=True, side=tk.RIGHT)
        
        self.preview_text = tk.Text(preview_frame, wrap=tk.WORD)
        self.preview_text.pack(fill=tk.BOTH, expand=True)
        
        # Status bar
        self.status_bar = ttk.Label(self.root, text="Ready", relief=tk.SUNKEN)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        
    def update_status(self, message: str) -> None:
        """Update the status bar"""
        self.status_bar.config(text=message)
        self.root.update_idletasks()
        
    def new_archive(self) -> None:
        """Create a new archive"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".crudearch",
            filetypes=[("CRUD Archive", "*.crudearch")]
        )
        
        if filename:
            self.archive_handler = CrudeArchiveHandler(filename)
            self.archive_handler.create(filename)
            self.current_file = filename
            self.update_file_list()
            self.update_status(f"New archive created: {filename}")
            
    def open_archive(self) -> None:
        """Open an existing archive"""
        filename = filedialog.askopenfilename(
            defaultextension=".crudearch",
            filetypes=[("CRUD Archive", "*.crudearch")]
        )
        
        if filename:
            try:
                self.archive_handler = CrudeArchiveHandler(filename)
                self.archive_handler.load()
                self.current_file = filename
                self.update_file_list()
                self.update_status(f"Archive opened: {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open archive: {str(e)}")
                
    def save_archive(self) -> None:
        """Save the current archive"""
        if self.archive_handler and self.current_file:
            try:
                self.archive_handler.save()
                self.update_status(f"Archive saved: {self.current_file}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save archive: {str(e)}")
        else:
            messagebox.showwarning("Warning", "No archive is currently open")
            
    def save_archive_as(self) -> None:
        """Save the current archive with a new name"""
        if self.archive_handler:
            filename = filedialog.asksaveasfilename(
                defaultextension=".crudearch",
                filetypes=[("CRUD Archive", "*.crudearch")]
            )
            
            if filename:
                self.archive_handler.filename = filename
                self.current_file = filename
                self.save_archive()
        else:
            messagebox.showwarning("Warning", "No archive is currently open")
            
    def update_file_list(self) -> None:
        """Update the file list display"""
        self.file_list.delete(*self.file_list.get_children())
        
        if self.archive_handler:
            for filename in self.archive_handler.list_files():
                file_info = self.archive_handler.get_file_info(filename)
                self.file_list.insert('', 'end', text=filename, values=(file_info['type']))
                
    def on_file_select(self, event) -> None:
        """Handle file selection"""
        selection = self.file_list.selection()
        if selection and self.archive_handler:
            filename = self.file_list.item(selection[0])['text']
            try:
                content = self.archive_handler.get_file_as_text(filename)
                if content is not None:
                    self.preview_text.delete(1.0, tk.END)
                    self.preview_text.insert(tk.END, content)
                else:
                    file_info = self.archive_handler.get_file_info(filename)
                    if file_info:
                        self.preview_text.delete(1.0, tk.END)
                        self.preview_text.insert(tk.END, f"Binary content ({len(file_info['content'])} bytes)")
            except ValueError:
                file_info = self.archive_handler.get_file_info(filename)
                if file_info:
                    self.preview_text.delete(1.0, tk.END)
                    self.preview_text.insert(tk.END, f"Binary content ({len(file_info['content'])} bytes)")
    
    def add_file_dialog(self) -> None:
        """Open dialog to add a file to the archive"""
        if not self.archive_handler:
            messagebox.showwarning("Warning", "No archive is currently open")
            return
            
        filename = filedialog.askopenfilename(
            title="Select file to add to archive"
        )
        
        if filename:
            try:
                with open(filename, 'rb') as f:
                    content = f.read()
                
                name = os.path.basename(filename)
                file_type = name.split('.')[-1] if '.' in name else 'bin'
                
                self.archive_handler.add_file(name, content, file_type)
                self.update_file_list()
                self.update_status(f"Added file: {name}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add file: {str(e)}")
                
    def remove_file(self) -> None:
        """Remove the selected file from the archive"""
        if not self.archive_handler:
            messagebox.showwarning("Warning", "No archive is currently open")
            return
            
        selection = self.file_list.selection()
        if selection:
            filename = self.file_list.item(selection[0])['text']
            if messagebox.askyesno("Confirm", f"Remove file '{filename}' from archive?"):
                self.archive_handler.remove_file(filename)
                self.update_file_list()
                self.preview_text.delete(1.0, tk.END)
                self.update_status(f"Removed file: {filename}")
        else:
            messagebox.showwarning("Warning", "No file selected")


def run_gui():
    """Run the GUI application"""
    root = tk.Tk()
    app = CrudeArchiveManager(root)
    root.mainloop()

if __name__ == "__main__":
    run_gui()

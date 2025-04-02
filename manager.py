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
    """GUI application for managing CRUDE archives"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("CRUDE Archive Manager")
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
        
        self.add_export_menu()
        # File preview
        preview_frame = ttk.Labelframe(main_frame, text="File Preview")
        preview_frame.pack(fill=tk.BOTH, expand=True, side=tk.RIGHT)
        
        self.preview_text = tk.Text(preview_frame, wrap=tk.WORD)
        self.preview_text.pack(fill=tk.BOTH, expand=True)
        
        # Status bar
        self.status_bar = ttk.Label(self.root, text="Ready", relief=tk.SUNKEN)
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM)
    
    def add_export_menu(self):
        """Add export option to right-click menu"""
        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="Export File...", command=self.export_file)
        self.file_list.bind("<Button-3>", self.show_context_menu)
    
    
    def show_context_menu(self, event):
        """Show right-click menu"""
        item = self.file_list.identify_row(event.y)
        if item:
            self.file_list.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)

    def export_file(self):
        """Export selected file to disk"""
        selection = self.file_list.selection()
        if not selection or not self.archive_handler:
            return
    
        filename = self.file_list.item(selection[0])['text']
        file_info = self.archive_handler.get_file_info(filename)
        
        save_path = filedialog.asksaveasfilename(
            initialfile=filename,
            filetypes=[("All Files", "*.*")]
        )
        
        if save_path:
            try:
                with open(save_path, 'wb') as f:
                    f.write(file_info['content'])
                self.update_status(f"Exported: {filename} → {save_path}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export file: {str(e)}")

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
        """Handle file selection for all supported types"""
        selection = self.file_list.selection()
        if not selection or not self.archive_handler:
            return
    
        filename = self.file_list.item(selection[0])['text']
        file_info = self.archive_handler.get_file_info(filename)
        
        # Clear previous preview
        self.preview_text.delete(1.0, tk.END)
        
        # Get basic file info
        file_type = file_info['type'].lower()
        size = len(file_info['content'])
        self.preview_text.insert(tk.END, f"File: {filename}\nType: {file_type}\nSize: {size} bytes\n\n")
        
        # Handle different file categories
        if file_type in {'txt', 'json', 'xml', 'py', 'md'}:
            try:
                text_content = self.archive_handler.get_file_as_text(filename)
                self.preview_text.insert(tk.END, text_content)
            except Exception as e:
                self.preview_text.insert(tk.END, f"Cannot preview: {str(e)}")
        
        elif file_type in {'png', 'jpg', 'jpeg', 'gif', 'bmp'}:
            self.preview_text.insert(tk.END, "[Binary Image Data - Use Extract to access]")
        
        elif file_type in ArchiveCommon.MODEL_FORMATS['static'] | ArchiveCommon.MODEL_FORMATS['animated']:
            self.preview_text.insert(tk.END, f"[3D Model Data - {file_type.upper()} format]")
        
        elif file_type in {'npy', 'npz', 'hdf5'}:
            self.preview_text.insert(tk.END, "[Numeric Data - Use Extract to access]")
        
        else:
            self.preview_text.insert(tk.END, "[Binary Data - Use Extract to access]")

    def preview_image(self, image_data):
        """Preview image files while maintaining text widget availability"""
        try:
            from PIL import Image, ImageTk
            import io
            
            # Hide text widget temporarily
            self.preview_text.pack_forget()
            
            # Create image preview
            img = Image.open(io.BytesIO(image_data))
            img.thumbnail((400, 400))  # Limit size
            photo = ImageTk.PhotoImage(img)
            
            # Create and place image label
            img_label = tk.Label(self.preview_frame, image=photo)
            img_label.image = photo  # Keep reference
            img_label.pack(fill=tk.BOTH, expand=True)
            
        except ImportError:
            self.preview_text.delete(1.0, tk.END)
            self.preview_text.insert(tk.END, "Install Pillow for image preview")
            self.preview_text.pack(fill=tk.BOTH, expand=True)
        except Exception as e:
            self.preview_text.delete(1.0, tk.END)
            self.preview_text.insert(tk.END, f"Error previewing image: {str(e)}")
            self.preview_text.pack(fill=tk.BOTH, expand=True)
    
    def display_file_metadata(self, file_info, filename):
        """Display comprehensive file metadata in the preview text widget"""
        metadata = [
            f"File Name: {filename}",
            f"File Type: {file_info.get('type', 'Unknown')}",
            f"Size: {len(file_info.get('content', ''))} bytes",
            f"Compressed Size: {file_info.get('compress_size', 'N/A')} bytes",
            f"Modified: {file_info.get('date_time', 'Unknown')}",
            f"CRC: {file_info.get('CRC', 'N/A')}",
            f"Comment: {file_info.get('comment', 'None')}",
            f"Attributes: {file_info.get('external_attr', 'N/A')}",
            f"System: {file_info.get('create_system', 'N/A')}",
            f"Version: {file_info.get('extract_version', 'N/A')}",
            f"Flags: {file_info.get('flag_bits', 'N/A')}",
            f"Volume: {file_info.get('volume', 'N/A')}",
            f"Internal Attributes: {file_info.get('internal_attr', 'N/A')}",
            f"Header Offset: {file_info.get('header_offset', 'N/A')}"
        ]
        
        self.preview_text.delete(1.0, tk.END)
        for item in metadata:
            self.preview_text.insert(tk.END, item + "\n")


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

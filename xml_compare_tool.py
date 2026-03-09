import customtkinter as ctk
from tkinter import filedialog, messagebox
import xml.etree.ElementTree as ET
from pathlib import Path
import difflib
from typing import Dict, List, Tuple, Optional
import os

# Set appearance and theme
ctk.set_appearance_mode("dark")  # Modes: "System" (standard), "Dark", "Light"
ctk.set_default_color_theme("blue")  # Themes: "blue" (standard), "green", "dark-blue"

class ModernXMLCompareTool:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("XML Comparison Tool")
        self.root.geometry("1200x800")  # Reduced size for better visibility
        self.root.minsize(1000, 600)     # Set minimum size
        
        # Modern color scheme (customtkinter handles most colors automatically)
        self.colors = {
            'primary': '#1f6aa5',
            'success': '#0d8f4b',
            'warning': '#d48806',
            'error': '#d32f2f',
            'surface': '#212121',
            'background': '#1a1a1a'
        }
        
        # File paths
        self.suc_file_path = None
        self.xml_file_path = None
        
        # Data storage
        self.suc_data = {}
        self.xml_data = {}
        
        self.setup_modern_ui()
    
    def setup_modern_ui(self):
        # Configure grid weights
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(2, weight=1)
        
        # Header
        self.create_header()
        
        # File selection cards
        self.create_file_selection()
        
        # Action buttons
        self.create_action_buttons()
        
        # Results section
        self.create_results_section()
    
    def create_header(self):
        header_frame = ctk.CTkFrame(self.root, corner_radius=0)
        header_frame.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 8))
        header_frame.grid_columnconfigure(0, weight=1)
        
        # Title
        title_label = ctk.CTkLabel(
            header_frame,
            text="🔍 SAP Confirmation Validator",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.grid(row=0, column=0, sticky="w", padx=15, pady=(15, 3))
        
        # Subtitle
        subtitle_label = ctk.CTkLabel(
            header_frame,
            text="Verify all AdditionalProperties from EAO orders are returned in XML reports",
            font=ctk.CTkFont(size=12)
        )
        subtitle_label.grid(row=1, column=0, sticky="w", padx=15, pady=(0, 12))
    
    def create_file_selection(self):
        file_frame = ctk.CTkFrame(self.root)
        file_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=8)
        file_frame.grid_columnconfigure(0, weight=1)
        file_frame.grid_columnconfigure(1, weight=1)
        
        # SUC File Card
        self.create_file_card(file_frame, "📁 EAO Order File", "Select .eao.suc file with production orders", self.select_suc_file, 0)
        
        # XML File Card
        self.create_file_card(file_frame, "📄 XML Report", "Select exported XML report file", self.select_xml_file, 1)
    
    def create_file_card(self, parent, title, subtitle, command, column):
        card_frame = ctk.CTkFrame(parent)
        card_frame.grid(row=0, column=column, padx=(0 if column == 0 else 8, 8 if column == 0 else 0), sticky="nsew")
        card_frame.grid_rowconfigure(2, weight=1)
        
        # Title
        title_label = ctk.CTkLabel(
            card_frame,
            text=title,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        title_label.grid(row=0, column=0, sticky="w", padx=15, pady=(15, 3))
        
        # Subtitle
        subtitle_label = ctk.CTkLabel(
            card_frame,
            text=subtitle,
            font=ctk.CTkFont(size=11)
        )
        subtitle_label.grid(row=1, column=0, sticky="w", padx=15, pady=(0, 8))
        
        # File name display
        file_label = ctk.CTkLabel(
            card_frame,
            text="No file selected",
            font=ctk.CTkFont(size=10),
            text_color=("gray70", "gray30")
        )
        file_label.grid(row=2, column=0, sticky="ew", padx=15, pady=(0, 10))
        
        # Browse button
        browse_btn = ctk.CTkButton(
            card_frame,
            text="Browse Files",
            command=command,
            font=ctk.CTkFont(size=11, weight="bold"),
            height=28
        )
        browse_btn.grid(row=3, column=0, padx=15, pady=(0, 15), sticky="ew")
        
        # Store references
        if column == 0:
            self.suc_label = file_label
        else:
            self.xml_label = file_label
    
    def create_action_buttons(self):
        button_frame = ctk.CTkFrame(self.root)
        button_frame.grid(row=2, column=0, sticky="ew", padx=15, pady=8)
        
        # Compare button
        self.compare_btn = ctk.CTkButton(
            button_frame,
            text="🔍 Validate SAP Properties",
            command=self.compare_files,
            font=ctk.CTkFont(size=12, weight="bold"),
            height=35,
            width=180
        )
        self.compare_btn.pack(side="left", padx=(15, 8))
        
        # Clear button
        clear_btn = ctk.CTkButton(
            button_frame,
            text="🗑️ Clear",
            command=self.clear_results,
            font=ctk.CTkFont(size=11),
            height=35,
            width=100,
            fg_color=("gray75", "gray25"),
            hover_color=("gray65", "gray35")
        )
        clear_btn.pack(side="left", padx=8)
        
        # Export button
        self.export_btn = ctk.CTkButton(
            button_frame,
            text="📄 Export Report",
            command=self.export_report,
            font=ctk.CTkFont(size=11),
            height=35,
            width=120,
            fg_color=self.colors['success'],
            hover_color="#0a7c3e",
            state="disabled"
        )
        self.export_btn.pack(side="left", padx=8)
        
        # Theme toggle
        theme_switch = ctk.CTkSwitch(
            button_frame,
            text="🌙 Dark Mode",
            command=self.toggle_theme
        )
        theme_switch.pack(side="right", padx=(8, 15))
    
    def create_results_section(self):
        # Results container with tabs
        self.tabview = ctk.CTkTabview(self.root)
        self.tabview.grid(row=3, column=0, sticky="nsew", padx=15, pady=(8, 15))
        self.tabview.grid_columnconfigure(0, weight=1)
        self.tabview.grid_rowconfigure(0, weight=1)
        
        # Create tabs
        self.create_overview_tab()
        self.create_missing_properties_tab()
        self.create_details_tab()
    
    def create_overview_tab(self):
        tab = self.tabview.add("📊 Validation Summary")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_columnconfigure(1, weight=1)
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)
        
        # Create summary cards
        self.overview_cards = {}
        card_configs = [
            ("Total Parts", "0", self.colors['primary'], 0, 0),
            ("Valid Parts", "0", self.colors['success'], 1, 0),
            ("Missing Properties", "0", self.colors['error'], 0, 1),
            ("Validation Rate", "0%", self.colors['warning'], 1, 1)
        ]
        
        for title, value, color, col, row in card_configs:
            card = self.create_summary_card(tab, title, value, color, col, row)
            self.overview_cards[title] = card
    
    def create_summary_card(self, parent, title, value, color, column, row):
        card_frame = ctk.CTkFrame(parent, fg_color=color)
        card_frame.grid(row=row, column=column, padx=8, pady=8, sticky="nsew")
        
        # Value
        value_label = ctk.CTkLabel(
            card_frame,
            text=value,
            font=ctk.CTkFont(size=28, weight="bold"),
            text_color="white"
        )
        value_label.pack(pady=(15, 3))
        
        # Title
        title_label = ctk.CTkLabel(
            card_frame,
            text=title,
            font=ctk.CTkFont(size=12),
            text_color="white"
        )
        title_label.pack(pady=(0, 15))
        
        return value_label
    
    def create_missing_properties_tab(self):
        tab = self.tabview.add("⚠️ Missing SAP Properties")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)
        
        # Scrollable frame for differences
        self.differences_scroll = ctk.CTkScrollableFrame(tab)
        self.differences_scroll.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        
        # Initial message
        self.differences_label = ctk.CTkLabel(
            self.differences_scroll,
            text="📋 Select files and validate to see missing SAP properties",
            font=ctk.CTkFont(size=13),
            text_color=("gray50", "gray40")
        )
        self.differences_label.pack(pady=30)
    
    def create_details_tab(self):
        tab = self.tabview.add("📋 Details")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)
        
        # Create legend frame at the top
        legend_frame = ctk.CTkFrame(tab)
        legend_frame.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 4))
        legend_frame.grid_columnconfigure(0, weight=1)
        
        # Legend title
        legend_title = ctk.CTkLabel(
            legend_frame,
            text="🔍 Validation Status Legend:",
            font=ctk.CTkFont(size=12, weight="bold")
        )
        legend_title.pack(anchor="w", padx=15, pady=(10, 5))
        
        # Legend items container
        legend_items = ctk.CTkFrame(legend_frame)
        legend_items.pack(fill="x", padx=15, pady=(0, 10))
        
        # Create legend items
        self.create_legend_item(legend_items, "🔴 Missing", "#ff6b6b", "Property exists in one file but not the other")
        self.create_legend_item(legend_items, "🟡 Different", "#feca57", "Property exists in both files but values don't match")
        self.create_legend_item(legend_items, "🔵 Match", "#48dbfb", "Property exists in both files with identical values")
        
        # Create treeview for detailed results
        tree_frame = ctk.CTkFrame(tab)
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)
        
        # Use tkinter Treeview with customtkinter styling
        import tkinter as tk
        from tkinter import ttk
        
        # Create tkinter frame for treeview
        tk_frame = tk.Frame(tree_frame, bg="#212121")
        tk_frame.grid(row=0, column=0, sticky="nsew")
        
        # Modern treeview
        columns = ('Part Name', 'Property', 'EAO Value', 'XML Value', 'Status')
        self.results_tree = ttk.Treeview(tk_frame, columns=columns, show='tree headings', height=20)
        
        # Configure columns
        self.results_tree.heading('#0', text='Category')
        self.results_tree.column('#0', width=150)
        
        for col in columns:
            self.results_tree.heading(col, text=col)
            if col == 'Part Name':
                self.results_tree.column(col, width=120)
            elif col == 'Property':
                self.results_tree.column(col, width=150)
            elif col == 'Status':
                self.results_tree.column(col, width=100)
            else:
                self.results_tree.column(col, width=200)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(tk_frame, orient=tk.VERTICAL, command=self.results_tree.yview)
        h_scrollbar = ttk.Scrollbar(tk_frame, orient=tk.HORIZONTAL, command=self.results_tree.xview)
        self.results_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Grid layout
        self.results_tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        tk_frame.grid_columnconfigure(0, weight=1)
        tk_frame.grid_rowconfigure(0, weight=1)
        
        # Configure tags with modern colors
        self.results_tree.tag_configure('missing', foreground='#ff6b6b')
        self.results_tree.tag_configure('different', foreground='#feca57')
        self.results_tree.tag_configure('match', foreground='#48dbfb')
        self.results_tree.tag_configure('header', font=('Segoe UI', 10, 'bold'))
    
    def toggle_theme(self):
        # Toggle between dark and light mode
        current_mode = ctk.get_appearance_mode()
        new_mode = "light" if current_mode == "Dark" else "dark"
        ctk.set_appearance_mode(new_mode)
    
    def select_suc_file(self):
        file_path = filedialog.askopenfilename(
            title="Select SUC File",
            filetypes=[("SUC files", "*.suc"), ("XML files", "*.xml"), ("All files", "*.*")]
        )
        if file_path:
            self.suc_file_path = file_path
            self.suc_label.configure(text=os.path.basename(file_path), text_color=ctk.ThemeManager.theme["CTkLabel"]["text_color"])
    
    def select_xml_file(self):
        file_path = filedialog.askopenfilename(
            title="Select XML Report File",
            filetypes=[("XML files", "*.xml"), ("All files", "*.*")]
        )
        if file_path:
            self.xml_file_path = file_path
            self.xml_label.configure(text=os.path.basename(file_path), text_color=ctk.ThemeManager.theme["CTkLabel"]["text_color"])
    
    def parse_suc_file(self, file_path: str) -> Dict[str, Dict[str, str]]:
        """Parse SUC file and extract additional properties grouped by part name"""
        data = {}
        
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Find all ErpOrderItem elements at any level
            for item in root.findall('.//ErpOrderItem'):
                name = item.find('Name')
                workstep = item.find('Workstep')
                
                if name is not None:
                    part_name = name.text  # Use just the part name as the key
                    if part_name not in data:
                        data[part_name] = {}
                    
                    # Get AdditionalProperties from this workstep
                    add_props = item.find('AdditionalProperties')
                    if add_props is not None:
                        for prop in add_props.findall('AdditionalProperty'):
                            prop_id = prop.get('id')
                            prop_value = prop.text
                            if prop_id and prop_value:
                                # Store with workstep prefix to avoid conflicts
                                workstep_prefix = f"{workstep.text}_" if workstep else ""
                                data[part_name][f"{workstep_prefix}{prop_id}"] = prop_value.strip()
                    
        except Exception as e:
            messagebox.showerror("Error", f"Error parsing SUC file: {str(e)}")
            return {}
        
        return data
    
    def parse_xml_report(self, file_path: str) -> Dict[str, Dict[str, str]]:
        """Parse XML report file and extract additional properties grouped by part name"""
        data = {}
        
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()
            
            # Find all Part elements
            for part in root.findall('.//Part'):
                name = part.find('Name')
                
                if name is not None:
                    part_name = name.text  # Use just the part name as the key
                    if part_name not in data:
                        data[part_name] = {}
                    
                    # Get AdditionalProperties
                    add_props = part.find('AdditionalProperties')
                    if add_props is not None:
                        for prop in add_props.findall('AdditionalProperty'):
                            prop_id = prop.get('id')
                            prop_value = prop.text
                            if prop_id and prop_value:
                                data[part_name][prop_id] = prop_value.strip()
                    
        except Exception as e:
            messagebox.showerror("Error", f"Error parsing XML report: {str(e)}")
            return {}
        
        return data
    
    def compare_files(self):
        """Validate SAP properties between EAO order and XML report"""
        if not self.suc_file_path or not self.xml_file_path:
            messagebox.showwarning("Warning", "Please select both EAO order and XML report files")
            return
        
        # Clear previous results
        self.clear_results()
        
        # Show loading state
        self.compare_btn.configure(text="🔄 Validating...", state="disabled")
        self.root.update()
        
        # Parse files
        self.suc_data = self.parse_suc_file(self.suc_file_path)
        self.xml_data = self.parse_xml_report(self.xml_file_path)
        
        # Perform validation and display results
        self.display_validation_results()
        
        # Reset button
        self.compare_btn.configure(text="🔍 Validate SAP Properties", state="normal")
        self.export_btn.configure(state="normal")
    
    def display_validation_results(self):
        """Display SAP validation results in modern format"""
        
        # Get all unique part names and properties
        all_parts = set(self.suc_data.keys()) | set(self.xml_data.keys())
        all_properties = set()
        for props in self.suc_data.values():
            all_properties.update(props.keys())
        for props in self.xml_data.values():
            all_properties.update(props.keys())
        
        # Calculate validation statistics
        total_suc_parts = len(self.suc_data)
        total_xml_parts = len(self.xml_data)
        common_parts = len(set(self.suc_data.keys()) & set(self.xml_data.keys()))
        
        # Count missing SAP properties
        missing_properties_count = 0
        valid_parts_count = 0
        
        for part_name in all_parts:
            suc_props = self.suc_data.get(part_name, {})
            xml_props = self.xml_data.get(part_name, {})
            
            if part_name in self.suc_data and part_name in self.xml_data:
                part_valid = True
                for prop_name in suc_props.keys():
                    if prop_name not in xml_props:
                        missing_properties_count += 1
                        part_valid = False
                if part_valid:
                    valid_parts_count += 1
            else:
                missing_properties_count += len(suc_props.get(part_name, {}))
        
        # Calculate validation rate
        validation_rate = 0
        if total_suc_parts > 0:
            validation_rate = (valid_parts_count / total_suc_parts) * 100
        
        # Update overview cards
        self.overview_cards["Total Parts"].configure(text=str(total_suc_parts))
        self.overview_cards["Valid Parts"].configure(text=str(valid_parts_count))
        self.overview_cards["Missing Properties"].configure(text=str(missing_properties_count))
        self.overview_cards["Validation Rate"].configure(text=f"{validation_rate:.1f}%")
        
        # Display missing properties in the validation tab
        self.display_missing_properties(all_parts, all_properties)
        
        # Display detailed results in the details tab
        self.display_detailed_results(all_parts, all_properties)
    
    def display_missing_properties(self, all_parts, all_properties):
        """Display missing SAP properties in a clean, modern format"""
        # Clear existing differences
        for widget in self.differences_scroll.winfo_children():
            widget.destroy()
        
        missing_found = False
        
        # Find missing SAP properties for each part
        for part_name in sorted(all_parts):
            suc_props = self.suc_data.get(part_name, {})
            xml_props = self.xml_data.get(part_name, {})
            
            part_missing = []
            
            # Check if part exists in both files
            if part_name not in self.suc_data:
                part_missing.append(("no_eao", "Part not found in EAO order file", "", ""))
                missing_found = True
            elif part_name not in self.xml_data:
                part_missing.append(("no_xml", "Part not found in XML report", "", ""))
                missing_found = True
            else:
                # Check for missing SAP properties
                for prop_name in sorted(suc_props.keys()):
                    if prop_name not in xml_props:
                        suc_value = suc_props[prop_name]
                        part_missing.append(("missing_property", prop_name, suc_value, "MISSING"))
                        missing_found = True
            
            # Create validation card for this part if issues exist
            if part_missing:
                self.create_validation_card(part_name, part_missing)
        
        if not missing_found:
            # Show success message
            success_label = ctk.CTkLabel(
                self.differences_scroll,
                text="✅ All SAP Properties Valid!\n\nEvery AdditionalProperty from EAO orders is present in the XML report.",
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color=self.colors['success']
            )
            success_label.pack(pady=50)
    
    def create_validation_card(self, part_name, validation_issues):
        """Create a modern card for displaying SAP validation issues"""
        card_frame = ctk.CTkFrame(self.differences_scroll)
        card_frame.pack(fill="x", padx=10, pady=10)
        
        # Part header
        header_label = ctk.CTkLabel(
            card_frame,
            text=f"🔧 {part_name}",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        header_label.pack(anchor="w", padx=15, pady=(15, 10))
        
        # Validation issues content
        for issue_type, prop_name, suc_val, xml_val in validation_issues:
            issue_frame = ctk.CTkFrame(card_frame)
            issue_frame.pack(fill="x", padx=15, pady=(0, 8))
            
            # Property name
            prop_label = ctk.CTkLabel(
                issue_frame,
                text=prop_name,
                font=ctk.CTkFont(size=11, weight="bold"),
                width=200,
                anchor="w"
            )
            prop_label.pack(side="left", padx=(10, 10))
            
            # EAO value
            eao_label = ctk.CTkLabel(
                issue_frame,
                text=f"EAO: {suc_val or 'N/A'}",
                font=ctk.CTkFont(size=10),
                width=180,
                anchor="w",
                text_color=("gray50", "gray40")
            )
            eao_label.pack(side="left", padx=(0, 10))
            
            # Arrow
            arrow_label = ctk.CTkLabel(
                issue_frame,
                text="→",
                font=ctk.CTkFont(size=12)
            )
            arrow_label.pack(side="left", padx=(0, 10))
            
            # XML value
            xml_label = ctk.CTkLabel(
                issue_frame,
                text=f"XML: {xml_val or 'N/A'}",
                font=ctk.CTkFont(size=10),
                width=180,
                anchor="w",
                text_color=self.colors['error'] if xml_val == "MISSING" else ("gray50", "gray40")
            )
            xml_label.pack(side="left")
            
            # Status indicator
            if issue_type == "no_eao":
                status_text = "❌ Missing in EAO"
                status_color = self.colors['error']
            elif issue_type == "no_xml":
                status_text = "❌ Missing in XML"
                status_color = self.colors['error']
            else:
                status_text = "❌ Missing SAP Property"
                status_color = self.colors['error']
            
            status_label = ctk.CTkLabel(
                issue_frame,
                text=status_text,
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color=status_color
            )
            status_label.pack(side="right", padx=(10, 10))
    
    def create_legend_item(self, parent, status_text, color, description):
        """Create a legend item with color indicator"""
        item_frame = ctk.CTkFrame(parent)
        item_frame.pack(side="left", padx=(0, 20))
        
        # Color indicator (using a small label with colored text)
        color_label = ctk.CTkLabel(
            item_frame,
            text="●",
            font=ctk.CTkFont(size=16),
            text_color=color
        )
        color_label.pack(side="left", padx=(0, 8))
        
        # Status text
        status_label = ctk.CTkLabel(
            item_frame,
            text=status_text,
            font=ctk.CTkFont(size=10, weight="bold")
        )
        status_label.pack(side="left", padx=(0, 5))
        
        # Description
        desc_label = ctk.CTkLabel(
            item_frame,
            text=f"- {description}",
            font=ctk.CTkFont(size=9),
            text_color=("gray60", "gray40")
        )
        desc_label.pack(side="left")
    
    def display_detailed_results(self, all_parts, all_properties):
        """Display detailed results in the treeview"""
        
        # Clear previous results
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        
        # Summary node
        summary_node = self.results_tree.insert('', 'end', text='📊 Summary', tags=('header',))
        
        total_suc_parts = len(self.suc_data)
        total_xml_parts = len(self.xml_data)
        common_parts = len(set(self.suc_data.keys()) & set(self.xml_data.keys()))
        
        self.results_tree.insert(summary_node, 'end', text='Statistics', values=(
            f'', f'', 
            f'EAO Parts: {total_suc_parts}', 
            f'XML Parts: {total_xml_parts}', 
            f'Common: {common_parts}'
        ))
        
        # Compare each part
        for part_name in sorted(all_parts):
            part_node = self.results_tree.insert('', 'end', text=f'🔧 {part_name}', tags=('header',))
            
            suc_props = self.suc_data.get(part_name, {})
            xml_props = self.xml_data.get(part_name, {})
            
            # Check for missing parts
            if part_name not in self.suc_data:
                self.results_tree.insert(part_node, 'end', text='Missing in SUC', values=(
                    part_name, 'N/A', 'MISSING', 'Available', 'missing'
                ))
                continue
            
            if part_name not in self.xml_data:
                self.results_tree.insert(part_node, 'end', text='Missing in XML', values=(
                    part_name, 'N/A', 'Available', 'MISSING', 'missing'
                ))
                continue
            
            # Compare properties
            for prop_name in sorted(all_properties):
                suc_value = suc_props.get(prop_name, 'N/A')
                xml_value = xml_props.get(prop_name, 'N/A')
                
                if suc_value == 'N/A' and xml_value != 'N/A':
                    status = 'missing'
                    status_text = 'Missing in SUC'
                elif xml_value == 'N/A' and suc_value != 'N/A':
                    status = 'missing'
                    status_text = 'Missing in XML'
                elif suc_value != xml_value:
                    status = 'different'
                    status_text = 'Different'
                else:
                    status = 'match'
                    status_text = 'Match'
                
                if suc_value != 'N/A' or xml_value != 'N/A':
                    self.results_tree.insert(part_node, 'end', text=f'📋 {prop_name}', 
                                           values=(part_name, prop_name, suc_value, xml_value, status_text),
                                           tags=(status,))
    
    def clear_results(self):
        """Clear all results from the interface"""
        # Clear treeview
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        
        # Clear differences container
        for widget in self.differences_scroll.winfo_children():
            widget.destroy()
        
        # Reset overview cards
        for card in self.overview_cards.values():
            card.configure(text="0")
        
        # Reset validation rate card
        self.overview_cards["Validation Rate"].configure(text="0%")
        
        # Disable export button
        self.export_btn.configure(state="disabled")
        
        # Show initial message
        self.differences_label = ctk.CTkLabel(
            self.differences_scroll,
            text="📋 Select files and validate to see missing SAP properties",
            font=ctk.CTkFont(size=13),
            text_color=("gray50", "gray40")
        )
        self.differences_label.pack(pady=30)
    
    def export_report(self):
        """Export comparison results to a text file"""
        if not self.results_tree.get_children():
            messagebox.showwarning("Warning", "No results to export")
            return
        
        file_path = filedialog.asksaveasfilename(
            title="Save Comparison Report",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write("XML Comparison Report\n")
                    f.write("=" * 50 + "\n\n")
                    f.write(f"SUC File: {self.suc_file_path}\n")
                    f.write(f"XML File: {self.xml_file_path}\n\n")
                    
                    def write_tree(parent_node, indent=0):
                        for child in self.results_tree.get_children(parent_node):
                            item_text = self.results_tree.item(child)['text']
                            item_values = self.results_tree.item(child)['values']
                            
                            if item_values:
                                f.write(f"{'  ' * indent}{item_text}: {item_values}\n")
                            else:
                                f.write(f"{'  ' * indent}{item_text}\n")
                            
                            write_tree(child, indent + 1)
                    
                    write_tree('')
                
                messagebox.showinfo("Success", f"Report exported to {file_path}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Error exporting report: {str(e)}")
    
    def run(self):
        self.root.mainloop()

def main():
    app = ModernXMLCompareTool()
    app.run()

if __name__ == "__main__":
    main()

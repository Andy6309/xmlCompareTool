"""
SAP Confirmation Validator Core Logic
Handles XML parsing, validation, and report generation
"""

import xml.etree.ElementTree as ET
import pandas as pd
import json
from datetime import datetime
from typing import Dict, List, Tuple
import io

# PDF generation imports
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False


class SAPConfirmationValidator:
    """Core SAP validation logic"""
    
    def __init__(self):
        self.eao_data = {}
        self.xml_data = {}
    
    def parse_eao_file(self, file_content: str) -> Dict[str, Dict[str, str]]:
        """Parse EAO file and extract additional properties from both blanking and nesting worksteps"""
        data = {}
        
        try:
            root = ET.fromstring(file_content)
            
            # Find all ErpOrderItem elements at any level
            for item in root.findall('.//ErpOrderItem'):
                name = item.find('Name')
                workstep = item.find('Workstep')
                
                if name is not None and workstep is not None:
                    part_name = name.text  # Use just the part name as the key
                    workstep_name = workstep.text
                    
                    if part_name not in data:
                        data[part_name] = {}
                    
                    # Get AdditionalProperties from this workstep (both blanking and nesting)
                    add_props = item.find('AdditionalProperties')
                    if add_props is not None:
                        for prop in add_props.findall('AdditionalProperty'):
                            prop_id = prop.get('id')
                            prop_value = prop.text
                            if prop_id and prop_value:
                                # Store with workstep prefix for clarity
                                # For duplicate properties (like PartProdOrder), keep both with workstep prefix
                                workstep_prefix = f"{workstep_name}_"
                                data[part_name][f"{workstep_prefix}{prop_id}"] = prop_value.strip()
                        
            # Debug: Print what we found for verification
            for part_name, props in data.items():
                print(f"Part {part_name} has {len(props)} properties:")
                for prop_name, prop_value in props.items():
                    print(f"  {prop_name}: {prop_value}")
                        
        except Exception as e:
            raise Exception(f"Error parsing EAO file: {str(e)}")
        
        return data
    
    def parse_xml_report(self, file_content: str) -> Dict[str, Dict[str, str]]:
        """Parse XML report file and extract additional properties grouped by part name"""
        data = {}
        
        try:
            root = ET.fromstring(file_content)
            
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
            raise Exception(f"Error parsing XML report: {str(e)}")
        
        return data
    
    def validate_properties(self, eao_data: Dict, xml_data: Dict) -> Dict:
        """Validate SAP properties between EAO order and XML report"""
        validation_results = {
            'total_parts': len(eao_data),
            'valid_parts': 0,
            'missing_properties_count': 0,
            'validation_rate': 0.0,
            'issues': [],
            'detailed_results': []
        }
        
        # Get all unique part names
        all_parts = set(eao_data.keys()) | set(xml_data.keys())
        
        # Count missing SAP properties and validate each part
        for part_name in sorted(all_parts):
            eao_props = eao_data.get(part_name, {})
            xml_props = xml_data.get(part_name, {})
            
            part_issues = []
            part_valid = True
            
            # Check if part exists in both files
            if part_name not in eao_data:
                part_issues.append({
                    'type': 'no_eao',
                    'property': 'Part not found in EAO order file',
                    'eao_value': '',
                    'xml_value': '',
                    'status': 'Missing in EAO'
                })
                validation_results['missing_properties_count'] += len(xml_props)
                part_valid = False
            elif part_name not in xml_data:
                part_issues.append({
                    'type': 'no_xml',
                    'property': 'Part not found in XML report',
                    'eao_value': '',
                    'xml_value': '',
                    'status': 'Missing in XML'
                })
                validation_results['missing_properties_count'] += len(eao_props)
                part_valid = False
            else:
                # Create a mapping of EAO properties to base property names for comparison
                # XML only has base names (no workstep prefixes)
                eao_base_props = {}
                for prop_key, prop_value in eao_props.items():
                    if '_' in prop_key:
                        # Remove workstep prefix (e.g., "Blanking_PartProdOrder" -> "PartProdOrder")
                        base_prop = prop_key.split('_', 1)[1]
                        # If property already exists, prioritize nesting over blanking
                        if base_prop not in eao_base_props or 'Nesting_' in prop_key:
                            eao_base_props[base_prop] = prop_value
                    else:
                        eao_base_props[prop_key] = prop_value
                
                # Check for missing SAP properties (using base names)
                for prop_name in eao_base_props.keys():
                    if prop_name not in xml_props:
                        eao_value = eao_base_props[prop_name]
                        part_issues.append({
                            'type': 'missing_property',
                            'property': prop_name,
                            'eao_value': eao_value,
                            'xml_value': 'MISSING',
                            'status': 'Missing SAP Property'
                        })
                        validation_results['missing_properties_count'] += 1
                        part_valid = False
                
                # Add detailed comparison (using base names for matching)
                for prop_name in set(eao_base_props.keys()) | set(xml_props.keys()):
                    eao_value = eao_base_props.get(prop_name, 'N/A')
                    xml_value = xml_props.get(prop_name, 'N/A')
                    
                    if eao_value == 'N/A' and xml_value != 'N/A':
                        status = 'Missing in EAO'
                        status_color = 'error'
                    elif xml_value == 'N/A' and eao_value != 'N/A':
                        status = 'Missing in XML'
                        status_color = 'error'
                    elif eao_value != xml_value:
                        status = 'Different'
                        status_color = 'warning'
                    else:
                        status = 'Match'
                        status_color = 'success'
                    
                    validation_results['detailed_results'].append({
                        'part_name': part_name,
                        'property': prop_name,
                        'eao_value': eao_value,
                        'xml_value': xml_value,
                        'status': status,
                        'status_color': status_color
                    })
            
            if part_valid and part_name in eao_data and part_name in xml_data:
                validation_results['valid_parts'] += 1
            
            # Add to issues if any found
            if part_issues:
                validation_results['issues'].append({
                    'part_name': part_name,
                    'issues': part_issues
                })
        
        # Calculate validation rate
        if validation_results['total_parts'] > 0:
            validation_results['validation_rate'] = (validation_results['valid_parts'] / validation_results['total_parts']) * 100
        
        return validation_results


class ReportGenerator:
    """Handles report generation in various formats"""
    
    @staticmethod
    def generate_pdf_report(validation_results: Dict) -> bytes:
        """Generate a professional PDF report"""
        if not PDF_AVAILABLE:
            return None
        
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)
        
        # Get styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.darkblue
        )
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=12,
            textColor=colors.darkblue
        )
        
        # Build story
        story = []
        
        # Title
        story.append(Paragraph("SAP Confirmation Validator Report", title_style))
        story.append(Spacer(1, 12))
        
        # Timestamp
        story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Executive Summary
        story.append(Paragraph("Executive Summary", heading_style))
        story.append(Spacer(1, 12))
        
        summary_data = [
            ['Metric', 'Value'],
            ['Total Parts Validated', str(validation_results['total_parts'])],
            ['Parts with Complete SAP Data', str(validation_results['valid_parts'])],
            ['Missing SAP Properties', str(validation_results['missing_properties_count'])],
            ['Validation Success Rate', f"{validation_results['validation_rate']:.1f}%"]
        ]
        
        summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(summary_table)
        story.append(Spacer(1, 20))
        
        # Detailed Results
        if validation_results['detailed_results']:
            story.append(Paragraph("Detailed Validation Results", heading_style))
            story.append(Spacer(1, 12))
            
            # Group by part
            grouped_results = {}
            for result in validation_results['detailed_results']:
                part_name = result['part_name']
                if part_name not in grouped_results:
                    grouped_results[part_name] = []
                grouped_results[part_name].append(result)
            
            for part_name in sorted(grouped_results.keys()):
                part_results = grouped_results[part_name]
                issue_count = sum(1 for r in part_results if r['status'] != 'Match')
                
                story.append(Paragraph(f"Part: {part_name} ({len(part_results)} properties, {issue_count} issues)", styles['Heading3']))
                
                # Table for this part
                table_data = [['SAP Property', 'EAO Value', 'XML Value', 'Status']]
                for result in part_results:
                    table_data.append([
                        result['property'],
                        result['eao_value'] or 'N/A',
                        result['xml_value'] or 'N/A',
                        result['status']
                    ])
                
                part_table = Table(table_data, colWidths=[2*inch, 2*inch, 2*inch, 1.5*inch])
                part_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black),
                    ('FONTSIZE', (0, 1), (-1, -1), 9)
                ]))
                
                story.append(part_table)
                story.append(Spacer(1, 12))
                
                if issue_count > 0:
                    story.append(Paragraph(f"Warning: {issue_count} properties need attention", styles['Normal']))
                else:
                    story.append(Paragraph("Success: All properties valid", styles['Normal']))
                
                story.append(Spacer(1, 12))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
    
    @staticmethod
    def generate_json_report(validation_results: Dict) -> str:
        """Generate JSON report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_parts': validation_results['total_parts'],
                'valid_parts': validation_results['valid_parts'],
                'missing_properties_count': validation_results['missing_properties_count'],
                'validation_rate': validation_results['validation_rate']
            },
            'issues': validation_results['issues'],
            'detailed_results': validation_results['detailed_results']
        }
        return json.dumps(report, indent=2)
    
    @staticmethod
    def generate_excel_report(validation_results: Dict) -> bytes:
        """Generate Excel report"""
        try:
            import openpyxl
        except ImportError:
            return None
        
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            # Summary sheet
            summary_df = pd.DataFrame([
                ['Total Parts', validation_results['total_parts']],
                ['Valid Parts', validation_results['valid_parts']],
                ['Missing Properties', validation_results['missing_properties_count']],
                ['Validation Rate', f"{validation_results['validation_rate']:.1f}%"]
            ], columns=['Metric', 'Value'])
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Detailed results sheet
            df = pd.DataFrame(validation_results['detailed_results'])
            df.to_excel(writer, sheet_name='Detailed Results', index=False)
        
        excel_buffer.seek(0)
        return excel_buffer.getvalue()
    
    @staticmethod
    def generate_csv_report(validation_results: Dict) -> str:
        """Generate CSV report"""
        df = pd.DataFrame(validation_results['detailed_results'])
        return df.to_csv(index=False)
    
    @staticmethod
    def generate_email_summary(validation_results: Dict) -> str:
        """Generate email-friendly summary"""
        return f"""
SAP Validation Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Summary:
- Total Parts: {validation_results['total_parts']}
- Valid Parts: {validation_results['valid_parts']}
- Missing Properties: {validation_results['missing_properties_count']}
- Validation Rate: {validation_results['validation_rate']:.1f}%

Issues Found: {len(validation_results['issues'])} parts have validation issues.

Generated by SAP Confirmation Validator
        """.strip()

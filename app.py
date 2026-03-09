import streamlit as st
import pandas as pd
import xml.etree.ElementTree as ET
from pathlib import Path
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import base64
import io
from typing import Dict, List, Tuple
import os
from datetime import datetime
import json

# PDF generation imports
try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

# Set page configuration
st.set_page_config(
    page_title="SAP Confirmation Validator",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    .metric-value {
        font-size: 2.5rem;
        font-weight: bold;
        margin-bottom: 0.5rem;
    }
    .metric-label {
        font-size: 1rem;
        opacity: 0.9;
    }
    .success-card {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
    }
    .error-card {
        background: linear-gradient(135deg, #eb3349 0%, #f45c43 100%);
    }
    .warning-card {
        background: linear-gradient(135deg, #f2994a 0%, #f2c94c 100%);
    }
    .primary-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    .stFileUploader {
        border: 2px dashed #667eea;
        border-radius: 10px;
        padding: 2rem;
        text-align: center;
    }
    .validation-issue {
        background-color: #fff5f5;
        border-left: 4px solid #f56565;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0 5px 5px 0;
    }
    .validation-issue strong {
        color: #2d3748 !important;
        font-weight: 600 !important;
    }
    .validation-issue small {
        color: #4a5568 !important;
        font-weight: 500 !important;
    }
    .success-message {
        background-color: #f0fff4;
        border-left: 4px solid #48bb78;
        padding: 1rem;
        margin: 0.5rem 0;
        border-radius: 0 5px 5px 0;
    }
</style>
""", unsafe_allow_html=True)

class SAPConfirmationValidator:
    def __init__(self):
        self.eao_data = {}
        self.xml_data = {}
    
    def parse_eao_file(self, file_content: str) -> Dict[str, Dict[str, str]]:
        """Parse EAO file and extract additional properties grouped by part name"""
        data = {}
        
        try:
            root = ET.fromstring(file_content)
            
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
            st.error(f"Error parsing EAO file: {str(e)}")
            return {}
        
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
            st.error(f"Error parsing XML report: {str(e)}")
            return {}
        
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
                validation_results['missing_properties_count'] += len(eao_props)
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
                # Check for missing SAP properties
                for prop_name in eao_props.keys():
                    if prop_name not in xml_props:
                        eao_value = eao_props[prop_name]
                        part_issues.append({
                            'type': 'missing_property',
                            'property': prop_name,
                            'eao_value': eao_value,
                            'xml_value': 'MISSING',
                            'status': 'Missing SAP Property'
                        })
                        validation_results['missing_properties_count'] += 1
                        part_valid = False
            
            if part_valid and part_name in eao_data and part_name in xml_data:
                validation_results['valid_parts'] += 1
            
            # Add to issues if any found
            if part_issues:
                validation_results['issues'].append({
                    'part_name': part_name,
                    'issues': part_issues
                })
            
            # Add detailed comparison
            for prop_name in set(eao_props.keys()) | set(xml_props.keys()):
                eao_value = eao_props.get(prop_name, 'N/A')
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
        
        # Calculate validation rate
        if validation_results['total_parts'] > 0:
            validation_results['validation_rate'] = (validation_results['valid_parts'] / validation_results['total_parts']) * 100
        
        return validation_results

def create_metric_cards(validation_results: Dict):
    """Create metric cards for the dashboard"""
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card primary-card">
            <div class="metric-value">{validation_results['total_parts']}</div>
            <div class="metric-label">Total Parts</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card success-card">
            <div class="metric-value">{validation_results['valid_parts']}</div>
            <div class="metric-label">Valid Parts</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card error-card">
            <div class="metric-value">{validation_results['missing_properties_count']}</div>
            <div class="metric-label">Missing Properties</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown(f"""
        <div class="metric-card warning-card">
            <div class="metric-value">{validation_results['validation_rate']:.1f}%</div>
            <div class="metric-label">Validation Rate</div>
        </div>
        """, unsafe_allow_html=True)

def create_validation_chart(validation_results: Dict):
    """Create a validation chart"""
    fig = go.Figure()
    
    labels = ['Valid Parts', 'Invalid Parts']
    values = [validation_results['valid_parts'], 
              validation_results['total_parts'] - validation_results['valid_parts']]
    colors = ['#11998e', '#eb3349']
    
    fig.add_trace(go.Pie(
        labels=labels,
        values=values,
        hole=0.4,
        marker_colors=colors,
        textinfo='label+percent+value',
        textposition='outside'
    ))
    
    fig.update_layout(
        title="Validation Results Distribution",
        font=dict(size=14),
        showlegend=True,
        height=400
    )
    
    st.plotly_chart(fig, use_container_width=True)

def display_missing_properties(validation_results: Dict):
    """Display missing SAP properties with expand/collapse controls"""
    if not validation_results['issues']:
        st.markdown("""
        <div class="success-message">
            <h3>All SAP Properties Valid!</h3>
            <p>Every AdditionalProperty from EAO orders is present in the XML report.</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Add expand/collapse controls
        col1, col2 = st.columns([1, 4])
        with col1:
            if st.button("📂 Expand All", key="expand_missing"):
                st.session_state.expand_missing_all = True
            if st.button("📁 Collapse All", key="collapse_missing"):
                st.session_state.expand_missing_all = False
        
        # Initialize session state if not exists
        if 'expand_missing_all' not in st.session_state:
            st.session_state.expand_missing_all = False
        
        st.markdown("### Missing SAP Properties by Part")
        
        for part_issue in validation_results['issues']:
            part_name = part_issue['part_name']
            issues = part_issue['issues']
            
            # Determine if this should be expanded
            expanded = st.session_state.expand_missing_all
            
            with st.expander(f"{part_name} ({len(issues)} issues)", expanded=expanded):
                for issue in issues:
                    st.markdown(f"""
                    <div class="validation-issue">
                        <strong>{issue['property']}</strong><br>
                        <small>EAO: {issue['eao_value'] or 'N/A'} → XML: {issue['xml_value'] or 'N/A'}</small><br>
                        <strong>Status: {issue['status']}</strong>
                    </div>
                    """, unsafe_allow_html=True)

def display_detailed_results(validation_results: Dict):
    """Display detailed results in a better grouped format with expand/collapse controls"""
    if not validation_results['detailed_results']:
        st.info("No detailed results to display.")
        return
    
    # Group results by part name
    grouped_results = {}
    for result in validation_results['detailed_results']:
        part_name = result['part_name']
        if part_name not in grouped_results:
            grouped_results[part_name] = []
        grouped_results[part_name].append(result)
    
    # Add expand/collapse controls
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("📂 Expand All", key="expand_details"):
            st.session_state.expand_details_all = True
        if st.button("📁 Collapse All", key="collapse_details"):
            st.session_state.expand_details_all = False
    
    # Initialize session state if not exists
    if 'expand_details_all' not in st.session_state:
        st.session_state.expand_details_all = False
    
    # Display results grouped by part
    st.markdown("### Detailed Validation Results")
    
    for part_name in sorted(grouped_results.keys()):
        part_results = grouped_results[part_name]
        
        # Count issues for this part
        issue_count = sum(1 for r in part_results if r['status'] != 'Match')
        
        # Determine if this should be expanded
        expanded = st.session_state.expand_details_all or issue_count > 0
        
        # Create expandable section for each part
        with st.expander(f"{part_name} ({len(part_results)} properties, {issue_count} issues)", expanded=expanded):
            # Create a cleaner table for this part
            part_df = pd.DataFrame(part_results)
            
            # Rename columns for clarity BEFORE styling
            part_df = part_df.rename(columns={
                'property': 'SAP Property',
                'eao_value': 'EAO Value',
                'xml_value': 'XML Value',
                'status': 'Status'
            })
            
            # Add color coding
            def color_status(val):
                if val == 'Match':
                    return 'background-color: #e6ffed; color: #22543d'
                elif val == 'Missing in EAO' or val == 'Missing in XML':
                    return 'background-color: #fff5f5; color: #742a2a'
                else:
                    return 'background-color: #fffbf0; color: #744210'
            
            # Apply styling
            styled_df = part_df.style.applymap(color_status, subset=['Status'])
            
            st.dataframe(styled_df, use_container_width=True, hide_index=True)
            
            # Add summary for this part
            if issue_count > 0:
                st.warning(f"{issue_count} properties need attention for part {part_name}")
            else:
                st.success(f"All properties valid for part {part_name}")

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

def create_export_section(validation_results: Dict):
    """Create comprehensive export section"""
    st.markdown("### Export Options")
    
    if not validation_results['detailed_results']:
        st.warning("No results to export.")
        return
    
    # Create columns for different export options
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # CSV Export
        df = pd.DataFrame(validation_results['detailed_results'])
        csv = df.to_csv(index=False)
        
        st.download_button(
            label="📊 CSV Report",
            data=csv,
            file_name=f"sap_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col2:
        # Excel Export (if available)
        try:
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
            
            st.download_button(
                label="📈 Excel Report",
                data=excel_buffer.getvalue(),
                file_name=f"sap_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        except ImportError:
            # Silently disable Excel export if openpyxl not available
            st.download_button(
                label="📈 Excel Report (Unavailable)",
                data="",
                file_name="excel_unavailable.txt",
                mime="text/plain",
                disabled=True,
                use_container_width=True
            )
    
    with col3:
        # PDF Export
        if PDF_AVAILABLE:
            pdf_data = generate_pdf_report(validation_results)
            if pdf_data:
                st.download_button(
                    label="📄 PDF Report",
                    data=pdf_data,
                    file_name=f"sap_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            else:
                st.download_button(
                    label="📄 PDF Report (Error)",
                    data="",
                    file_name="pdf_error.txt",
                    mime="text/plain",
                    disabled=True,
                    use_container_width=True
                )
        else:
            # Silently disable PDF export if reportlab not available
            st.download_button(
                label="📄 PDF Report (Unavailable)",
                data="",
                file_name="pdf_unavailable.txt",
                mime="text/plain",
                disabled=True,
                use_container_width=True
            )
    
    with col4:
        # JSON Export
        json_data = generate_json_report(validation_results)
        st.download_button(
            label="📋 JSON Report",
            data=json_data,
            file_name=f"sap_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )
    
    # Additional options
    st.markdown("---")
    st.markdown("### Additional Export Options")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Print-friendly version
        if st.button("🖨️ Generate Print-Friendly Version"):
            st.markdown("""
            <style>
            @media print {
                .stApp { display: none; }
                .print-content { display: block !important; }
            }
            </style>
            <div class="print-content">
            """, unsafe_allow_html=True)
            
            # Print-friendly summary
            st.markdown("#### SAP Validation Report")
            st.markdown(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            col_print1, col_print2 = st.columns(2)
            with col_print1:
                st.metric("Total Parts", validation_results['total_parts'])
                st.metric("Valid Parts", validation_results['valid_parts'])
            with col_print2:
                st.metric("Missing Properties", validation_results['missing_properties_count'])
                st.metric("Validation Rate", f"{validation_results['validation_rate']:.1f}%")
            
            st.markdown("</div>", unsafe_allow_html=True)
            st.info("Use your browser's print function (Ctrl+P) to print this report")
    
    with col2:
        # Email report (copy to clipboard)
        if st.button("📧 Copy Report Summary"):
            summary_text = f"""
SAP Validation Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Summary:
- Total Parts: {validation_results['total_parts']}
- Valid Parts: {validation_results['valid_parts']}
- Missing Properties: {validation_results['missing_properties_count']}
- Validation Rate: {validation_results['validation_rate']:.1f}%

Issues Found: {len(validation_results['issues'])} parts have validation issues.

Generated by SAP Confirmation Validator
            """.strip()
            
            st.code(summary_text)
            st.success("Summary copied to clipboard! Paste into email or document.")

def export_results(validation_results: Dict):
    """Legacy export function - now redirects to comprehensive export"""
    create_export_section(validation_results)

def main():
    # Initialize session state
    if 'validator' not in st.session_state:
        st.session_state.validator = SAPConfirmationValidator()
    if 'validation_results' not in st.session_state:
        st.session_state.validation_results = None
    
    # Header
    st.markdown('<h1 class="main-header">SAP Confirmation Validator</h1>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Verify all AdditionalProperties from EAO orders are returned in XML reports</p>', unsafe_allow_html=True)
    
    # File upload section
    st.markdown("### Upload Files")
    col1, col2 = st.columns(2)
    
    with col1:
        eao_file = st.file_uploader(
            "EAO Order File (.eao.suc)",
            type=['suc', 'xml'],
            key="eao_file",
            help="Upload the EAO order file containing production orders"
        )
    
    with col2:
        xml_file = st.file_uploader(
            "XML Report (.xml)",
            type=['xml'],
            key="xml_file",
            help="Upload the exported XML report file"
        )
    
    # Validation button
    if eao_file and xml_file:
        if st.button("Validate SAP Properties", type="primary", use_container_width=True):
            with st.spinner("Validating SAP properties..."):
                # Parse files
                eao_content = eao_file.read().decode('utf-8')
                xml_content = xml_file.read().decode('utf-8')
                
                eao_data = st.session_state.validator.parse_eao_file(eao_content)
                xml_data = st.session_state.validator.parse_xml_report(xml_content)
                
                # Validate properties
                validation_results = st.session_state.validator.validate_properties(eao_data, xml_data)
                st.session_state.validation_results = validation_results
                
                # Store data for detailed views
                st.session_state.eao_data = eao_data
                st.session_state.xml_data = xml_data
    
    # Display results
    if st.session_state.validation_results:
        validation_results = st.session_state.validation_results
        
        # Export Options at the TOP
        create_export_section(validation_results)
        
        # Metric cards
        create_metric_cards(validation_results)
        
        # Tabs for different views
        tab1, tab2, tab3 = st.tabs(["Validation Summary", "Missing Properties", "Detailed Results"])
        
        with tab1:
            st.markdown("### Validation Overview")
            create_validation_chart(validation_results)
            
            # Summary statistics
            st.markdown("### Summary Statistics")
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Total Parts Validated", validation_results['total_parts'])
                st.metric("Parts with Complete SAP Data", validation_results['valid_parts'])
            
            with col2:
                st.metric("Missing SAP Properties", validation_results['missing_properties_count'])
                st.metric("Validation Success Rate", f"{validation_results['validation_rate']:.1f}%")
        
        with tab2:
            display_missing_properties(validation_results)
        
        with tab3:
            display_detailed_results(validation_results)
    
    # Footer
    st.markdown("---")
    st.markdown(
        "<div style='text-align: center; color: #666; margin-top: 2rem;'>"
        "SAP Confirmation Validator • Ensure seamless ERP integration"
        "</div>", 
        unsafe_allow_html=True
    )

if __name__ == "__main__":
    main()

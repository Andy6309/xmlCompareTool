"""
SAP Confirmation Validator - Streamlit Web Application
Main application entry point with proper Streamlit structure
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import io
import os

# Import core functionality
from utils.sap_validator import SAPConfirmationValidator, ReportGenerator, PDF_AVAILABLE
from utils.sample_data import load_default_samples, get_sample_files

# Configure page
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


def create_metric_cards(validation_results: dict):
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


def create_validation_chart(validation_results: dict):
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


def display_missing_properties(validation_results: dict):
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


def display_detailed_results(validation_results: dict):
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


def create_export_section(validation_results: dict):
    """Create comprehensive export section"""
    st.markdown("### Export Options")
    
    if not validation_results['detailed_results']:
        st.warning("No results to export.")
        return
    
    # Create columns for different export options
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # CSV Export
        csv_data = ReportGenerator.generate_csv_report(validation_results)
        
        st.download_button(
            label="CSV Report",
            data=csv_data,
            file_name=f"sap_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col2:
        # Excel Export
        excel_data = ReportGenerator.generate_excel_report(validation_results)
        if excel_data:
            st.download_button(
                label="Excel Report",
                data=excel_data,
                file_name=f"sap_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        else:
            st.download_button(
                label="Excel Report (Unavailable)",
                data="",
                file_name="excel_unavailable.txt",
                mime="text/plain",
                disabled=True,
                use_container_width=True
            )
    
    with col3:
        # PDF Export
        if PDF_AVAILABLE:
            pdf_data = ReportGenerator.generate_pdf_report(validation_results)
            if pdf_data:
                st.download_button(
                    label="PDF Report",
                    data=pdf_data,
                    file_name=f"sap_validation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            else:
                st.download_button(
                    label="PDF Report (Error)",
                    data="",
                    file_name="pdf_error.txt",
                    mime="text/plain",
                    disabled=True,
                    use_container_width=True
                )
        else:
            st.download_button(
                label="PDF Report (Unavailable)",
                data="",
                file_name="pdf_unavailable.txt",
                mime="text/plain",
                disabled=True,
                use_container_width=True
            )
    
    with col4:
        # JSON Export
        json_data = ReportGenerator.generate_json_report(validation_results)
        st.download_button(
            label="JSON Report",
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
        if st.button("Generate Print-Friendly Version"):
            st.markdown("#### SAP Validation Report")
            st.markdown(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            col_print1, col_print2 = st.columns(2)
            with col_print1:
                st.metric("Total Parts", validation_results['total_parts'])
                st.metric("Valid Parts", validation_results['valid_parts'])
            with col_print2:
                st.metric("Missing Properties", validation_results['missing_properties_count'])
                st.metric("Validation Rate", f"{validation_results['validation_rate']:.1f}%")
            
            st.info("Use your browser's print function (Ctrl+P) to print this report")
    
    with col2:
        # Email report (copy to clipboard)
        if st.button("Copy Report Summary"):
            summary_text = ReportGenerator.generate_email_summary(validation_results)
            st.code(summary_text)
            st.success("Summary copied to clipboard! Paste into email or document.")


def main():
    """Main application function"""
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
    
    # Check if sample files are available
    sample_files = get_sample_files()
    has_samples = len(sample_files) > 0
    
    if has_samples:
        st.markdown("#### Quick Start: Load Sample Data")
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.info("Try our sample data to see the validator in action!")
        
        with col2:
            if st.button("Load Sample Files", type="secondary", use_container_width=True):
                with st.spinner("Loading sample data..."):
                    try:
                        samples = load_default_samples()
                        
                        if 'eao_file' in samples and 'xml_file' in samples:
                            # Store sample data in session state
                            st.session_state.sample_eao_content = samples['eao_file']
                            st.session_state.sample_xml_content = samples['xml_file']
                            st.session_state.using_samples = True
                            
                            # Parse and validate immediately
                            validator = SAPConfirmationValidator()
                            eao_data = validator.parse_eao_file(samples['eao_file'])
                            xml_data = validator.parse_xml_report(samples['xml_file'])
                            validation_results = validator.validate_properties(eao_data, xml_data)
                            st.session_state.validation_results = validation_results
                            st.session_state.validator = validator
                            
                            st.success("Sample data loaded and validated successfully!")
                            st.rerun()
                        else:
                            st.error("Sample files not found")
                    except Exception as e:
                        st.error(f"Error loading sample data: {str(e)}")
        
        with col3:
            if st.button("Clear Samples", use_container_width=True):
                st.session_state.using_samples = False
                if 'sample_eao_content' in st.session_state:
                    del st.session_state.sample_eao_content
                if 'sample_xml_content' in st.session_state:
                    del st.session_state.sample_xml_content
                if 'validation_results' in st.session_state:
                    del st.session_state.validation_results
                st.rerun()
        
        st.markdown("---")
        st.markdown("#### Or Upload Your Own Files")
    
    col1, col2 = st.columns(2)
    
    # Check if we're using sample data
    using_samples = st.session_state.get('using_samples', False)
    
    with col1:
        if using_samples and 'sample_eao_content' in st.session_state:
            st.success("Using sample EAO file")
            st.info("Sample: -V90063_64-20260224103356.eao.suc")
        else:
            eao_file = st.file_uploader(
                "EAO Order File (.eao.suc)",
                type=['suc', 'xml'],
                key="eao_file",
                help="Upload the EAO order file containing production orders"
            )
    
    with col2:
        if using_samples and 'sample_xml_content' in st.session_state:
            st.success("Using sample XML file")
            st.info("Sample: 20260225095318_-V90063_64_0224_01_20260225_095103.XML")
        else:
            xml_file = st.file_uploader(
                "XML Report (.xml)",
                type=['xml'],
                key="xml_file",
                help="Upload the exported XML report file"
            )
    
    # Validation button
    if using_samples or (eao_file and xml_file):
        if st.button("Validate SAP Properties", type="primary", use_container_width=True):
            with st.spinner("Validating SAP properties..."):
                try:
                    if using_samples:
                        # Use sample data
                        eao_content = st.session_state.sample_eao_content
                        xml_content = st.session_state.sample_xml_content
                    else:
                        # Use uploaded files
                        eao_content = eao_file.read().decode('utf-8')
                        xml_content = xml_file.read().decode('utf-8')
                    
                    # Parse files
                    eao_data = st.session_state.validator.parse_eao_file(eao_content)
                    xml_data = st.session_state.validator.parse_xml_report(xml_content)
                    
                    # Validate properties
                    validation_results = st.session_state.validator.validate_properties(eao_data, xml_data)
                    st.session_state.validation_results = validation_results
                    
                    if not using_samples:
                        st.success("Validation completed successfully!")
                    
                except Exception as e:
                    st.error(f"Error during validation: {str(e)}")
    
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

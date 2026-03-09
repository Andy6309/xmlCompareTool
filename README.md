# XML Comparison Tool

A Python application to compare `.suc` user order files with `.xml` exported reports and identify discrepancies in additional properties.

## Features

- **Modern UI**: Clean, user-friendly interface built with tkinter
- **File Selection**: Easy browsing for both SUC and XML report files
- **Property Comparison**: Detailed comparison of AdditionalProperties between files
- **Visual Results**: Color-coded display of differences (red=missing, orange=different, green=match)
- **Export Functionality**: Save comparison results to text files
- **Summary Statistics**: Overview of parts and properties comparison

## Usage

1. Run the application:
   ```bash
   python xml_compare_tool.py
   ```

2. Select your SUC file using the "Browse..." button
3. Select your XML report file using the "Browse..." button
4. Click "Compare Files" to analyze the differences
5. Review the results in the comparison table
6. Export results using "Export Report" if needed

## File Structure

- `xml_compare_tool.py` - Main application file
- `requirements.txt` - Dependencies (uses only standard library)
- `README.md` - This documentation

## Comparison Logic

The tool compares:
- **Part Names**: Identifies parts present in one file but missing in the other
- **Additional Properties**: For each matching part, compares all additional properties:
  - `PartProdOrder`
  - `PartNo`
  - `TotalOrderQty`
  - `NestedWC`
  - `RoutingSeq`
  - `ParentProdOrder`
  - `MaterialCode`
  - `WorkCenter`

## Result Categories

- **Missing in SUC**: Property exists in XML report but not in SUC file
- **Missing in XML**: Property exists in SUC file but not in XML report
- **Different**: Property exists in both files but with different values
- **Match**: Property exists in both files with identical values

## Requirements

- Python 3.6 or higher
- No external dependencies (uses only Python standard library)

## Notes

- The SUC file contains the original order data with ErpOrderItem elements
- The XML report contains the generated report with Part elements
- Both files use XML format but have different structures
- Additional properties are extracted and compared regardless of file structure differences

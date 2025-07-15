# Property Panel Integration Guide

The Property Panel Integration system provides seamless workspace integration, advanced editing capabilities, and comprehensive accessibility features for managing document element properties.

## Table of Contents

1. [Overview](#overview)
2. [Workspace Integration](#workspace-integration)
3. [Batch Editing](#batch-editing)
4. [Accessibility Features](#accessibility-features)
5. [Import/Export](#import-export)
6. [Keyboard Shortcuts](#keyboard-shortcuts)
7. [Troubleshooting](#troubleshooting)

## Overview

The Property Panel Integration system consists of four main components:

- **Workspace Integration**: Docking, layout management, and UI coordination
- **Batch Editing**: Efficient editing of multiple elements simultaneously
- **Accessibility Manager**: Screen reader support, keyboard navigation, and WCAG compliance
- **Import/Export**: Data exchange in multiple formats (JSON, CSV, XML, Pickle)

## Workspace Integration

### Panel Docking

The property panel can be docked to different areas of the main window:

- **Right Dock** (default): `Ctrl+Alt+Right` or View → Property Panel → Dock Right
- **Left Dock**: `Ctrl+Alt+Left` or View → Property Panel → Dock Left  
- **Bottom Dock**: `Ctrl+Alt+Down` or View → Property Panel → Dock Bottom
- **Floating**: `Ctrl+Alt+F` or View → Property Panel → Float Panel

### Panel Visibility

- **Toggle Visibility**: `F4` or View → Property Panel → Show/Hide
- **Focus Panel**: `Ctrl+P` - Shows and focuses the property panel
- **Pin/Unpin**: `Ctrl+Shift+P` - Controls auto-hide behavior

### Workspace State Persistence

The system automatically saves and restores:
- Panel visibility state
- Dock position and floating state  
- Panel size and geometry
- Layout configurations per workspace perspective

## Batch Editing

### Overview

Batch editing allows you to modify properties across multiple selected elements efficiently.

### Basic Workflow

1. **Select Elements**: Use element list or document viewer to select multiple elements
2. **Open Batch Editor**: The batch editing panel appears when multiple elements are selected
3. **Choose Operation**: Select the property and operation type
4. **Configure Settings**: Set values, conditions, and filters
5. **Execute**: Run the batch operation with progress tracking

### Operation Types

#### Set Value
Replace property values across all selected elements:
```
Property: title
Operation: Set
Value: "Updated Title"
Target: All selected elements
```

#### Append Text
Add text to existing property values:
```
Property: content  
Operation: Append
Value: " - Reviewed"
Condition: Only if content is not empty
```

#### Replace Text
Find and replace text within property values:
```
Property: content
Operation: Replace
Find: "old text"
Replace: "new text"
Case Sensitive: No
```

#### Clear Values
Remove property values:
```
Property: temp_notes
Operation: Clear
Condition: Only if value matches pattern
```

### Conditional Operations

Apply operations only when conditions are met:

- **Value Conditions**: Check current property values
- **Type Conditions**: Filter by element type
- **Custom Functions**: Use JavaScript-like expressions

Example conditions:
```javascript
// Only if property is not empty
value != null && value.length > 0

// Only for specific element types
element.type == "text" || element.type == "title"

// Complex condition with multiple properties
element.confidence > 0.8 && element.content.length > 50
```

### Progress Tracking

Batch operations provide real-time feedback:
- **Progress Bar**: Shows completion percentage
- **Status Messages**: Current operation details
- **Error Reporting**: Detailed error information
- **Cancellation**: Stop operations in progress

## Accessibility Features

### Overview

Comprehensive accessibility support ensures the property panel is usable by everyone, including users with disabilities.

### Screen Reader Support

- **Automatic Announcements**: Property changes, focus changes, and navigation
- **Descriptive Labels**: All interactive elements have accessible names
- **Role Information**: Proper ARIA roles for complex widgets
- **Live Regions**: Dynamic content updates announced to screen readers

### Keyboard Navigation

#### Property Navigation
- `Tab` / `Shift+Tab`: Move between properties
- `Ctrl+Home` / `Ctrl+End`: First/last property
- `Ctrl+F`: Focus search box
- `F2`: Start editing focused property
- `Enter`: Commit changes
- `Escape`: Cancel editing

#### Panel Management  
- `F4`: Toggle panel visibility
- `Ctrl+P`: Focus property panel
- `Ctrl+Shift+P`: Pin/unpin panel
- `Ctrl+Alt+Arrow Keys`: Dock to different areas

#### Accessibility Features
- `Ctrl+Shift+Space`: Announce current focus
- `Ctrl+Alt+H`: Toggle high contrast mode
- `Ctrl+Plus` / `Ctrl+Minus`: Increase/decrease font size

### Visual Accessibility

#### High Contrast Mode
Automatically detected or manually enabled:
- High contrast color scheme
- Enhanced border visibility
- Bold text rendering
- Improved focus indicators

#### Font Scaling
Adjustable font sizes:
- Scale range: 50% to 200%
- Preserves layout integrity
- Affects all text elements
- Persists across sessions

#### Focus Indicators
Enhanced visual focus indicators:
- Animated border highlighting
- High contrast colors
- Keyboard navigation support
- Non-interfering positioning

## Import/Export

### Supported Formats

#### JSON Format
```json
{
  "export_info": {
    "timestamp": "2024-01-15T10:30:00",
    "format": "json",
    "element_count": 2
  },
  "elements": {
    "element_1": {
      "properties": {
        "title": "Document Title",
        "content": "Document content...",
        "type": "text"
      },
      "metadata": {
        "title": {
          "data_type": "string",
          "is_required": false
        }
      }
    }
  }
}
```

#### CSV Format
Flattened structure suitable for spreadsheet applications:
```csv
element_id,title,content,type,confidence
element_1,"Document Title","Document content...","text",0.95
element_2,"Section Header","Section content...","title",0.87
```

#### XML Format
Structured XML with proper hierarchy:
```xml
<property_export>
  <export_info>
    <timestamp>2024-01-15T10:30:00</timestamp>
    <format>xml</format>
  </export_info>
  <elements>
    <element id="element_1">
      <properties>
        <property name="title">Document Title</property>
        <property name="content">Document content...</property>
      </properties>
    </element>
  </elements>
</property_export>
```

### Export Configuration

#### Basic Options
- **Include Metadata**: Export property metadata along with values
- **Include Empty Values**: Export properties with null/empty values
- **Flatten Nested**: Convert nested objects to flat key-value pairs

#### Advanced Filtering
- **Element Filter**: Export only specific elements
- **Property Filter**: Export only selected properties
- **Custom Fields**: Add additional fields to export

### Import Configuration

#### Merge Strategies
- **Replace**: Overwrite existing property values
- **Merge**: Combine with existing data
- **Skip**: Ignore properties that already exist

#### Validation Options
- **Validate on Import**: Check data integrity during import
- **Create Backup**: Automatically backup before import
- **Ignore Errors**: Continue import despite validation errors

### Batch Import/Export Workflow

1. **Select Elements**: Choose elements for export or target for import
2. **Configure Format**: Select format and options
3. **Choose File Location**: Browse for import file or export destination
4. **Review Settings**: Confirm configuration options
5. **Execute Operation**: Monitor progress and handle any errors
6. **Verify Results**: Check imported/exported data integrity

## Keyboard Shortcuts

### Panel Management
| Shortcut | Action |
|----------|--------|
| `F4` | Toggle property panel visibility |
| `Ctrl+P` | Focus property panel |
| `Ctrl+Shift+P` | Pin/unpin panel |
| `Ctrl+Alt+Left` | Dock panel to left |
| `Ctrl+Alt+Right` | Dock panel to right |
| `Ctrl+Alt+Down` | Dock panel to bottom |
| `Ctrl+Alt+F` | Float panel |

### Navigation
| Shortcut | Action |
|----------|--------|
| `Tab` | Next property |
| `Shift+Tab` | Previous property |
| `Ctrl+Home` | First property |
| `Ctrl+End` | Last property |
| `Ctrl+F` | Focus search |

### Editing
| Shortcut | Action |
|----------|--------|
| `F2` | Start editing property |
| `Enter` | Commit changes |
| `Escape` | Cancel editing |
| `Ctrl+Z` | Undo last change |
| `Ctrl+Y` | Redo change |

### Batch Operations
| Shortcut | Action |
|----------|--------|
| `Ctrl+A` | Select all elements |
| `Ctrl+Shift+A` | Clear selection |
| `Ctrl+B` | Open batch editor |
| `Ctrl+Enter` | Execute batch operation |

### Accessibility
| Shortcut | Action |
|----------|--------|
| `Ctrl+Shift+Space` | Announce current focus |
| `Ctrl+Alt+H` | Toggle high contrast |
| `Ctrl+Plus` | Increase font size |
| `Ctrl+Minus` | Decrease font size |
| `Ctrl+0` | Reset font size |

### Groups and Sections
| Shortcut | Action |
|----------|--------|
| `Ctrl+Shift+Plus` | Expand all groups |
| `Ctrl+Shift+Minus` | Collapse all groups |
| `Left Arrow` | Collapse group |
| `Right Arrow` | Expand group |

## Troubleshooting

### Common Issues

#### Property Panel Not Visible
1. Check if panel is hidden: Press `F4` to toggle visibility
2. Check if panel is floating outside visible area: Reset workspace layout
3. Verify panel is not minimized in dock area

#### Keyboard Shortcuts Not Working
1. Ensure property panel has focus: Press `Ctrl+P`
2. Check for conflicting application shortcuts
3. Verify accessibility features are enabled
4. Restart application to reload shortcut bindings

#### Batch Operations Failing
1. Verify elements are properly selected
2. Check property names and types
3. Review operation conditions and syntax
4. Monitor error messages in batch editor

#### Import/Export Errors
1. Verify file format compatibility
2. Check file permissions and accessibility
3. Validate data structure and content
4. Review import configuration settings

#### Accessibility Issues
1. Enable screen reader detection in settings
2. Check system accessibility preferences
3. Verify high contrast and font scaling settings
4. Test with different input methods

### Performance Optimization

#### Large Datasets
- Use pagination for large element lists
- Enable batch operation progress tracking
- Consider splitting large operations
- Monitor memory usage during operations

#### UI Responsiveness
- Reduce number of visible properties
- Collapse unused property groups
- Disable animations if needed
- Use asynchronous operations for heavy tasks

### Getting Help

#### In-Application Help
- Press `F1` for context-sensitive help
- Use tooltip hover information
- Access help from View menu
- Check status bar for operation hints

#### Documentation Resources
- User guide documentation
- API reference for developers
- Video tutorials and examples
- Community forums and support

#### Reporting Issues
1. Note exact steps to reproduce
2. Include error messages and screenshots
3. Specify system configuration
4. Check known issues list first

For additional support, contact the TORE Matrix Labs team or visit the online documentation.
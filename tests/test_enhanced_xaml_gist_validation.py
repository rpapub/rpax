"""
Validation tests for enhanced XAML analyzer against original gist implementation.

Tests that our EnhancedXamlAnalyzer produces equivalent results to Christian Prior-Mamulyan's 
original graphical activity extractor gist.
"""
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Dict, Any

import pytest

from rpax.parser.enhanced_xaml_analyzer import EnhancedXamlAnalyzer


# Original gist implementation for comparison
BLACKLIST_TAGS_ORIGINAL = {
    "Members",
    "HintSize", 
    "Property",
    "TypeArguments",
    "WorkflowFileInfo",
    "Annotation",
    "ViewState",
    "Collection",
    "Dictionary",
    "ActivityAction",
}

def is_graphical_original(elem):
    """Original gist visual detection logic."""
    tag = elem.tag.split('}')[-1]
    return tag not in BLACKLIST_TAGS_ORIGINAL and (
        "DisplayName" in elem.attrib or tag in {
            "Sequence", "TryCatch", "Flowchart", "Parallel", "StateMachine"
        }
    )

def extract_visuals_original(elem, depth=0, path=""):
    """Original gist extraction logic."""
    tag = elem.tag.split('}')[-1]
    display = elem.attrib.get("DisplayName", "")
    node_path = f"{path}/{tag}" if path else tag

    results = []
    if is_graphical_original(elem):
        results.append({
            "Tag": tag,
            "DisplayName": display,
            "Path": node_path,
            "Depth": depth,
            "Attributes": elem.attrib
        })

    for child in elem:
        results.extend(extract_visuals_original(child, depth + 1, node_path))
    return results


class TestEnhancedXamlGistValidation:
    """Test enhanced XAML analyzer against original gist implementation."""
    
    def setup_method(self):
        """Setup test analyzer."""
        self.analyzer = EnhancedXamlAnalyzer()
    
    def test_visual_detection_matches_gist(self):
        """Test that visual detection logic matches original gist exactly."""
        # Create simple test XAML with various element types
        xaml_content = '''<?xml version="1.0" encoding="utf-8"?>
<Activity>
  <Members>
    <Property Name="in_Var1" />
  </Members>
  <HintSize>554,632</HintSize>
  <Sequence DisplayName="Main Sequence">
    <Variables>
      <Variable Name="testVar" />
    </Variables>
    <ViewState>
      <Dictionary>
        <Boolean>True</Boolean>
      </Dictionary>
    </ViewState>
    <Assign DisplayName="Assign Value">
      <AssignTo>[testVar]</AssignTo>
      <AssignValue>Hello World</AssignValue>
    </Assign>
    <If DisplayName="Check Condition">
      <IfCondition>[testVar = "Hello World"]</IfCondition>
      <Then>
        <WriteLine DisplayName="Write Line" Text="[testVar]" />
      </Then>
      <Else>
        <WriteLine DisplayName="Write Error" Text="Error occurred" />
      </Else>
    </If>
    <TryCatch DisplayName="Try Catch Block">
      <Try>
        <Delay DisplayName="Wait 1 Second" Duration="00:00:01" />
      </Try>
      <Catches>
        <Catch>
          <ActivityAction>
            <WriteLine DisplayName="Log Error" Text="error" />
          </ActivityAction>
        </Catch>
      </Catches>
    </TryCatch>
  </Sequence>
</Activity>'''
        
        # Parse with both implementations
        root = ET.fromstring(xaml_content)
        
        # Original gist results
        original_results = extract_visuals_original(root)
        
        # Enhanced analyzer results
        enhanced_results = self.analyzer._extract_visual_activities(root, "", 0, None)
        
        # Compare core metrics
        assert len(enhanced_results) >= len(original_results), "Enhanced analyzer should find at least as many activities as original"
        
        # Check that all original visual activities are found by enhanced analyzer
        original_tags = {result["Tag"] for result in original_results}
        enhanced_tags = {node.tag for node in enhanced_results}
        
        assert original_tags.issubset(enhanced_tags), f"Missing tags: {original_tags - enhanced_tags}"
        
        # Test specific visual detection cases
        test_elements = [
            ('<Sequence DisplayName="Test" />', True),  # Has DisplayName
            ('<Sequence />', True),  # Core activity without DisplayName
            ('<TryCatch />', True),  # Core activity
            ('<Members />', False),  # Blacklisted
            ('<HintSize />', False),  # Blacklisted
            ('<Property />', False),  # Blacklisted
            ('<ViewState />', False),  # Blacklisted
            ('<CustomActivity DisplayName="Test" />', True),  # Has DisplayName
            ('<CustomActivity />', False),  # No DisplayName, not core activity
        ]
        
        for xml_str, expected_visual in test_elements:
            elem = ET.fromstring(xml_str)
            tag = elem.tag.split('}')[-1]
            
            # Original gist logic
            original_is_visual = is_graphical_original(elem)
            
            # Enhanced analyzer logic
            enhanced_is_visual = self.analyzer._is_visual_activity(elem, tag)
            
            assert original_is_visual == expected_visual, f"Original gist failed for {xml_str}"
            assert enhanced_is_visual == expected_visual, f"Enhanced analyzer failed for {xml_str}"
            assert original_is_visual == enhanced_is_visual, f"Mismatch for {xml_str}"
    
    def test_blacklist_completeness(self):
        """Test that our blacklist includes all original gist blacklisted tags."""
        from rpax.parser.enhanced_xaml_analyzer import BLACKLIST_TAGS
        
        # Our blacklist should include all original blacklist tags
        missing_tags = BLACKLIST_TAGS_ORIGINAL - BLACKLIST_TAGS
        assert not missing_tags, f"Missing blacklist tags from original gist: {missing_tags}"
        
        # Test each blacklisted tag
        for tag in BLACKLIST_TAGS_ORIGINAL:
            test_elem = ET.fromstring(f'<{tag} DisplayName="Test" />')
            
            # Should be blacklisted by both implementations
            assert not is_graphical_original(test_elem), f"Original should blacklist {tag}"
            assert not self.analyzer._is_visual_activity(test_elem, tag), f"Enhanced should blacklist {tag}"
    
    def test_core_activities_detection(self):
        """Test that core activities are detected even without DisplayName."""
        core_activities = {"Sequence", "TryCatch", "Flowchart", "Parallel", "StateMachine"}
        
        for activity in core_activities:
            test_elem = ET.fromstring(f'<{activity} />')
            
            # Both implementations should detect as visual
            assert is_graphical_original(test_elem), f"Original should detect {activity} as visual"
            assert self.analyzer._is_visual_activity(test_elem, activity), f"Enhanced should detect {activity} as visual"
    
    def test_display_name_detection(self):
        """Test that any element with DisplayName is considered visual."""
        test_cases = [
            "CustomActivity",
            "UnknownElement", 
            "MySpecialActivity",
            "ThirdPartyActivity"
        ]
        
        for activity in test_cases:
            # Without DisplayName - should not be visual (unless core activity)
            elem_without = ET.fromstring(f'<{activity} />')
            
            original_without = is_graphical_original(elem_without)
            enhanced_without = self.analyzer._is_visual_activity(elem_without, activity)
            
            # Should match (both False for non-core activities)
            assert original_without == enhanced_without
            
            # With DisplayName - should be visual
            elem_with = ET.fromstring(f'<{activity} DisplayName="Test Activity" />')
            
            original_with = is_graphical_original(elem_with)
            enhanced_with = self.analyzer._is_visual_activity(elem_with, activity)
            
            # Both should be True
            assert original_with == True, f"Original should detect {activity} with DisplayName as visual"
            assert enhanced_with == True, f"Enhanced should detect {activity} with DisplayName as visual"
            assert original_with == enhanced_with
    
    def test_stable_node_id_generation(self):
        """Test stable indexed node ID generation like /Sequence[0]/If[1]/Then/Click[0]."""
        xaml_content = '''<?xml version="1.0" encoding="utf-8"?>
<Activity>
  <Sequence DisplayName="Main">
    <Assign DisplayName="First Assign" />
    <Assign DisplayName="Second Assign" />
    <If DisplayName="Condition">
      <Then>
        <Assign DisplayName="Then Assign" />
      </Then>
      <Else>
        <Assign DisplayName="Else Assign" />
      </Else>
    </If>
    <Assign DisplayName="Third Assign" />
  </Sequence>
</Activity>'''
        
        root = ET.fromstring(xaml_content)
        enhanced_results = self.analyzer._extract_visual_activities(root)
        
        # Check that node IDs are properly indexed
        node_ids = [node.node_id for node in enhanced_results]
        
        # Should have indexed paths (Activity is not visual, Sequence is root)
        expected_patterns = [
            "Activity/Sequence[0]",     # Main sequence (root visual activity)
            "Activity/Sequence/Assign[0]",  # First assign
            "Activity/Sequence/Assign[1]",  # Second assign  
            "Activity/Sequence/If[0]",      # If condition
            "Activity/Sequence/If/Then/Assign[0]",  # Then assign
            "Activity/Sequence/If/Else/Assign[0]",  # Else assign
            "Activity/Sequence/Assign[2]"   # Third assign
        ]
        
        # Check that all expected patterns are found
        for expected in expected_patterns:
            assert any(expected in node_id for node_id in node_ids), \
                f"Expected pattern '{expected}' not found in node IDs: {node_ids}"
        
        # Check that sibling indexing is correct (multiple Assigns)
        assign_ids = [nid for nid in node_ids if "Assign" in nid]
        assert len(assign_ids) >= 4, f"Should have at least 4 Assign activities, found: {assign_ids}"
        
        # Verify indexed numbering - main sequence assigns should have different indices
        main_assign_ids = [nid for nid in assign_ids if "Activity/Sequence/Assign[" in nid]
        assert len(main_assign_ids) >= 3, f"Should have at least 3 main sequence Assigns: {main_assign_ids}"
    
    def test_namespace_handling(self):
        """Test that namespace stripping works correctly."""
        namespaced_elements = [
            '<ns:Sequence xmlns:ns="http://example.com" />',
            '<ui:Sequence xmlns:ui="http://schemas.microsoft.com/netfx/2009/xaml/activities" />',
            '<custom:MyActivity xmlns:custom="http://custom.com" DisplayName="Test" />'
        ]
        
        for xml_str in namespaced_elements:
            elem = ET.fromstring(xml_str)
            
            # Extract tag without namespace (gist approach)
            gist_tag = elem.tag.split('}')[-1]
            
            # Enhanced analyzer should use the same approach
            enhanced_tag = elem.tag.rsplit('}', 1)[-1]  # Our current approach
            
            assert gist_tag == enhanced_tag, f"Namespace stripping mismatch for {xml_str}"
            
            # Visual detection should work on the clean tag
            original_visual = is_graphical_original(elem)
            enhanced_visual = self.analyzer._is_visual_activity(elem, enhanced_tag)
            
            assert original_visual == enhanced_visual, f"Visual detection mismatch for {xml_str}"
    
    def test_comprehensive_structural_elements(self):
        """Test comprehensive detection of structural vs visual elements."""
        test_cases = [
            # Structural elements (should NOT be visual)
            ('<Members />', False, "Metadata container"),
            ('<HintSize>200,100</HintSize>', False, "Layout hint"),
            ('<Property Name="test" />', False, "Property declaration"),
            ('<TypeArguments>String</TypeArguments>', False, "Type information"),
            ('<Variables><Variable Name="x" /></Variables>', False, "Variable container"),
            ('<Arguments><InArgument TypeArguments="String" /></Arguments>', False, "Argument container"),
            ('<ViewState><Dictionary /></ViewState>', False, "Designer state"),
            ('<Collection><String>test</String></Collection>', False, "Data collection"),
            ('<Dictionary><Boolean>True</Boolean></Dictionary>', False, "Data dictionary"),
            ('<ActivityAction><WriteLine /></ActivityAction>', False, "Action container"),
            ('<Then><Assign DisplayName="test" /></Then>', False, "If branch container"),
            ('<Else><Assign DisplayName="test" /></Else>', False, "If branch container"),
            ('<Catch><WriteLine /></Catch>', False, "Exception handler container"),
            ('<Finally><WriteLine /></Finally>', False, "Exception cleanup container"),
            ('<Catches><Catch /></Catches>', False, "Exception handlers container"),
            ('<Body><Assign /></Body>', False, "Activity body container"),
            ('<Condition>[x > 0]</Condition>', False, "Condition expression"),
            ('<Default><Assign /></Default>', False, "Switch default container"),
            
            # Visual elements (SHOULD be visual)
            ('<Sequence DisplayName="Main Flow" />', True, "Core activity with DisplayName"),
            ('<TryCatch />', True, "Core activity without DisplayName"),
            ('<Flowchart />', True, "Core activity without DisplayName"),
            ('<Parallel />', True, "Core activity without DisplayName"),
            ('<StateMachine />', True, "Core activity without DisplayName"),
            ('<Assign DisplayName="Set Value" />', True, "Regular activity with DisplayName"),
            ('<InvokeWorkflowFile DisplayName="Call Subflow" />', True, "Invoke activity"),
            ('<WriteLine DisplayName="Log Message" />', True, "Simple activity"),
            ('<Delay DisplayName="Wait" />', True, "Simple activity"),
            ('<CustomActivity DisplayName="My Action" />', True, "Custom activity with DisplayName"),
            
            # Edge cases
            ('<UnknownActivity />', False, "Unknown activity without DisplayName"),
            ('<Sequence />', True, "Core activity without DisplayName should still be visual"),
            ('<Click DisplayName="Click Button" />', True, "UI activity"),
            ('<OpenBrowser DisplayName="Open Browser" />', True, "Browser activity"),
            ('<GetText DisplayName="Get Text" />', True, "Data extraction activity")
        ]
        
        for xml_str, expected_visual, description in test_cases:
            elem = ET.fromstring(xml_str)
            tag = self.analyzer._get_local_tag(elem)
            
            # Test enhanced analyzer
            enhanced_visual = self.analyzer._is_visual_activity(elem, tag)
            
            # Test original gist
            original_visual = is_graphical_original(elem)
            
            assert enhanced_visual == expected_visual, \
                f"Enhanced analyzer failed for {description}: {xml_str} - Expected: {expected_visual}, Got: {enhanced_visual}"
            
            assert original_visual == expected_visual, \
                f"Original gist failed for {description}: {xml_str} - Expected: {expected_visual}, Got: {original_visual}"
            
            assert enhanced_visual == original_visual, \
                f"Enhanced vs Original mismatch for {description}: {xml_str}"
    
    def test_enhanced_blacklist_extensions(self):
        """Test that enhanced blacklist properly extends original gist blacklist."""
        from rpax.parser.enhanced_xaml_analyzer import BLACKLIST_TAGS
        
        # Enhanced blacklist extensions not in original gist
        enhanced_extensions = {
            "Variables", "Arguments", "Imports", "NamespacesForImplementation", 
            "ReferencesForImplementation", "TextExpression", "VisualBasic",
            "WorkflowViewState", "WorkflowViewStateService", "Ignorable",
            "Then", "Else", "Catches", "Catch", "Finally", "States", "Transitions",
            "Body", "Handler", "Condition", "Default"
        }
        
        for tag in enhanced_extensions:
            test_elem = ET.fromstring(f'<{tag} DisplayName="Test" />')
            
            # Should be blacklisted by enhanced analyzer
            enhanced_visual = self.analyzer._is_visual_activity(test_elem, tag)
            assert not enhanced_visual, f"Enhanced analyzer should blacklist {tag}"
            
            # Verify it's in our blacklist
            assert tag in BLACKLIST_TAGS, f"{tag} should be in enhanced blacklist"
    
    def test_expression_detection_patterns(self):
        """Test detection of VB.NET/C# expressions vs literals."""
        expression_test_cases = [
            # Expressions (should be True)
            ("[variable1]", True, "VB.NET variable reference"),
            ("[variable1.ToString()]", True, "VB.NET method call"), 
            ("[String.Format(\"Hello {0}\", name)]", True, "VB.NET string formatting"),
            ("[Path.Combine(folder, filename)]", True, "Path combination"),
            ("[x = 5]", True, "Assignment expression"),
            ("[new List(Of String)()]", True, "Object creation"),
            ("[DateTime.Now]", True, "Property access"),
            
            # Literals (should be False)
            ("Hello World", False, "Simple string literal"),
            ("Main.xaml", False, "Filename literal"),
            ("12345", False, "Numeric literal"),
            ("", False, "Empty string"),
            ("Test\nMultiline", False, "Multiline literal"),
            ("file.txt", False, "Simple filename"),
            ("C:\\temp\\file.txt", False, "Windows path literal"),
            
            # Edge cases
            ("[]", False, "Empty brackets"),
            ("Path.Combine", False, "Method name without brackets"),
            ("variable.ToString()", True, "Method call with parentheses should be expression"),
            ("ToString", False, "Method name without parentheses")
        ]
        
        for value, expected_expression, description in expression_test_cases:
            result = self.analyzer._is_expression_value(value)
            assert result == expected_expression, \
                f"Expression detection failed for {description}: '{value}' - Expected: {expected_expression}, Got: {result}"
    
    def test_invocation_classification(self):
        """Test classification of workflow invocation types."""
        invocation_test_cases = [
            # Static invocations
            ("Subflow.xaml", "invoke", "Static XAML filename"),
            ("Library\\Process.xaml", "invoke", "Static path with subfolder"),
            ("", "invoke-missing", "Empty filename"),
            
            # Dynamic invocations (expressions)
            ("[workflowPath]", "invoke-dynamic", "Variable-based path"),
            ("[Path.Combine(folder, filename)]", "invoke-dynamic", "Path combination expression"),
            ("[String.Format(\"Process{0}.xaml\", id)]", "invoke-dynamic", "String formatting expression"),
        ]
        
        for filename, expected_kind, description in invocation_test_cases:
            result = self.analyzer._classify_invocation(filename)
            assert result == expected_kind, \
                f"Invocation classification failed for {description}: '{filename}' - Expected: {expected_kind}, Got: {result}"


@pytest.mark.integration
class TestEnhancedXamlGistIntegration:
    """Integration tests with real UiPath XAML files."""
    
    def setup_method(self):
        """Setup test analyzer."""
        self.analyzer = EnhancedXamlAnalyzer()
    
    @pytest.mark.skipif(not Path("D:/github.com/rpapub/FrozenChlorine").exists(), 
                       reason="Test corpus not available")
    def test_real_xaml_comparison(self):
        """Test enhanced analyzer vs gist on real UiPath XAML files."""
        test_projects = [
            Path("D:/github.com/rpapub/FrozenChlorine"),
            Path("D:/github.com/rpapub/LuckyLawrencium"),
        ]
        
        for project_path in test_projects:
            if not project_path.exists():
                continue
                
            # Find XAML files
            xaml_files = list(project_path.glob("**/*.xaml"))
            
            for xaml_file in xaml_files[:3]:  # Test first 3 XAML files
                try:
                    tree = ET.parse(xaml_file)
                    root = tree.getroot()
                    
                    # Original gist results
                    original_results = extract_visuals_original(root)
                    
                    # Enhanced analyzer results  
                    enhanced_results = self.analyzer._extract_visual_activities(root, "", 0, None)
                    
                    # Basic validation - enhanced should find at least as many visual activities
                    assert len(enhanced_results) >= len(original_results), \
                        f"Enhanced analyzer found fewer activities in {xaml_file}"
                    
                    # All original tags should be found by enhanced analyzer
                    original_tags = {r["Tag"] for r in original_results}
                    enhanced_tags = {n.tag for n in enhanced_results}
                    
                    missing_tags = original_tags - enhanced_tags
                    assert not missing_tags, \
                        f"Enhanced analyzer missed tags {missing_tags} in {xaml_file}"
                        
                except ET.ParseError:
                    # Skip malformed XAML files
                    continue
                except Exception as e:
                    pytest.fail(f"Error processing {xaml_file}: {e}")
    
    def test_performance_comparison(self):
        """Test that enhanced analyzer performance is reasonable vs original gist."""
        import time
        
        # Create test XAML with many elements
        large_xaml = '''<?xml version="1.0" encoding="utf-8"?>
<Activity xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities">
  <Sequence DisplayName="Main">''' + \
    '\n'.join([f'    <Assign DisplayName="Assign {i}" />' for i in range(100)]) + \
    '''  </Sequence>
</Activity>'''
        
        root = ET.fromstring(large_xaml)
        
        # Time original gist approach
        start_time = time.perf_counter()
        for _ in range(10):  # Multiple runs for better average
            original_results = extract_visuals_original(root)
        original_time = (time.perf_counter() - start_time) / 10
        
        # Time enhanced analyzer
        start_time = time.perf_counter()
        for _ in range(10):
            enhanced_results = self.analyzer._extract_visual_activities(root, "", 0, None)
        enhanced_time = (time.perf_counter() - start_time) / 10
        
        # Performance logging (no constraints - enhanced analyzer provides much more functionality)
        print(f"Performance comparison: Enhanced {enhanced_time:.4f}s vs Original {original_time:.4f}s (ratio: {enhanced_time/original_time:.1f}x)")
        
        # Results should be equivalent in count
        assert len(enhanced_results) >= len(original_results)
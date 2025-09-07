"""Comprehensive tests for Activity instances extraction (ADR-009).

This test module validates the complete business logic extraction from UiPath activities
as first-class entities for MCP/LLM consumption.
"""

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from dataclasses import asdict

from src.xaml_parser.extractors import ActivityExtractor
from src.xaml_parser.models import Activity
from src.xaml_parser.utils import ActivityUtils


class TestActivityUtils:
    """Test activity utility functions."""
    
    def test_generate_activity_id_format(self):
        """Test stable activity ID generation format."""
        project_id = "test-proj-12345678"
        workflow_path = "Process/Calculator/ClickListOfCharacters.xaml"
        node_id = "Activity/Sequence/ForEach/Sequence/NApplicationCard/Sequence/If/Sequence/NClick_1"
        activity_content = "{'type': 'NClick', 'arguments': [('ActivateBefore', 'True')]}"
        
        activity_id = ActivityUtils.generate_activity_id(
            project_id, workflow_path, node_id, activity_content
        )
        
        # Verify format: {projectId}#{workflowId}#{nodeId}#{contentHash}
        parts = activity_id.split('#')
        assert len(parts) == 4
        assert parts[0] == project_id
        assert parts[1] == "Process/Calculator/ClickListOfCharacters"
        assert parts[2] == node_id
        assert len(parts[3]) == 8  # 8-character content hash
        assert all(c in '0123456789abcdef' for c in parts[3])  # Hex hash
    
    def test_generate_activity_id_stability(self):
        """Test that activity IDs are stable across runs."""
        project_id = "test-proj"
        workflow_path = "Main.xaml" 
        node_id = "Activity/Sequence/LogMessage_1"
        activity_content = "{'type': 'LogMessage', 'message': 'Hello'}"
        
        id1 = ActivityUtils.generate_activity_id(project_id, workflow_path, node_id, activity_content)
        id2 = ActivityUtils.generate_activity_id(project_id, workflow_path, node_id, activity_content)
        
        assert id1 == id2
    
    def test_generate_activity_id_content_sensitivity(self):
        """Test that different content produces different IDs."""
        project_id = "test-proj"
        workflow_path = "Main.xaml"
        node_id = "Activity/Sequence/LogMessage_1"
        
        id1 = ActivityUtils.generate_activity_id(project_id, workflow_path, node_id, "content1")
        id2 = ActivityUtils.generate_activity_id(project_id, workflow_path, node_id, "content2")
        
        assert id1 != id2
        # But project, workflow, node parts should be the same
        assert id1.split('#')[:3] == id2.split('#')[:3]
        assert id1.split('#')[3] != id2.split('#')[3]  # Different hash
    
    def test_extract_expressions_from_text(self):
        """Test expression extraction from UiPath text content."""
        test_cases = [
            # VB.NET expressions in brackets
            ('[currentItem.ToString]', ['currentItem.ToString']),
            ('[string.Format("Item: {0}", currentItem)]', ['string.Format("Item: {0}", currentItem)']),
            
            # Method calls
            ('currentItem.GetType().Name', ['currentItem.GetType()']),
            ('Path.Combine(folder, filename)', ['Path.Combine(folder, filename)']),
            
            # Mixed content
            ('Click on [string.Format("Button {0}", index)] element', 
             ['string.Format("Button {0}", index)']),
            
            # No expressions
            ('Simple text message', []),
            ('', []),
        ]
        
        for text, expected in test_cases:
            result = ActivityUtils.extract_expressions_from_text(text)
            # Convert to set for comparison (order doesn't matter)
            assert set(result) == set(expected), f"Failed for text: {text}"
    
    def test_extract_variable_references(self):
        """Test variable reference extraction from expressions."""
        test_cases = [
            # Simple variable references
            ('[currentItem]', ['currentItem']),
            ('[userName.ToString]', ['userName']),
            ('currentItem = newValue', ['currentItem']),
            
            # Multiple variables
            ('[string.Format("{0} - {1}", userName, currentDate)]', ['userName', 'currentDate']),
            
            # Filtered out common keywords
            ('[String.Empty]', []),
            ('[DateTime.Now]', []),
            ('If condition Then action', []),
            
            # Complex expressions
            ('[characterList.Count > 0]', ['characterList']),
            ('[in_Config("CredentialName").ToString]', ['in_Config']),
        ]
        
        for text, expected in test_cases:
            result = ActivityUtils.extract_variable_references(text)
            assert set(result) == set(expected), f"Failed for text: {text}"
    
    def test_extract_selectors_from_config(self):
        """Test UI selector extraction from configuration."""
        config = {
            'Target': {
                'FullSelector': '<webctrl id="submitBtn" tag="BUTTON" />',
                'FuzzySelector': '<fuzzy:selector accuracy="0.8" />',
                'TargetAnchorable': 'anchor_data'
            },
            'Properties': {
                'DisplayName': 'Click Submit Button',
                'ClickType': 'Single'
            },
            'NestedConfig': {
                'InnerTarget': {
                    'FullSelectorArgument': '<webctrl class="form-input" />',
                }
            }
        }
        
        selectors = ActivityUtils.extract_selectors_from_config(config)
        
        expected_selectors = {
            'Target.FullSelector': '<webctrl id="submitBtn" tag="BUTTON" />',
            'Target.FuzzySelector': '<fuzzy:selector accuracy="0.8" />',
            'Target.TargetAnchorable': 'anchor_data',
            'NestedConfig.InnerTarget.FullSelectorArgument': '<webctrl class="form-input" />'
        }
        
        assert selectors == expected_selectors
    
    def test_classify_activity_type(self):
        """Test activity type classification."""
        test_cases = [
            ('NClick', 'ui_automation'),
            ('TypeText', 'ui_automation'),
            ('GetFullText', 'ui_automation'),
            ('WaitForReady', 'ui_automation'),
            
            ('Sequence', 'flow_control'),
            ('If', 'flow_control'),
            ('ForEach', 'flow_control'),
            ('Parallel', 'flow_control'),
            
            ('Assign', 'data_processing'),
            ('InvokeWorkflowFile', 'data_processing'),
            ('BuildDataTable', 'data_processing'),
            
            ('LogMessage', 'system'),
            ('Delay', 'system'),
            ('KillProcess', 'system'),
            
            ('TryCatch', 'exception_handling'),
            ('Throw', 'exception_handling'),
            ('Rethrow', 'exception_handling'),
            
            ('CustomActivity', 'other'),
            ('UnknownType', 'other'),
        ]
        
        for activity_type, expected_category in test_cases:
            result = ActivityUtils.classify_activity_type(activity_type)
            assert result == expected_category, f"Failed for {activity_type}: expected {expected_category}, got {result}"


class TestActivityExtractor:
    """Test ActivityExtractor for complete business logic extraction."""
    
    @pytest.fixture
    def extractor(self):
        """Create ActivityExtractor with test configuration."""
        config = {
            'extract_expressions': True,
            'expression_language': 'VisualBasic'
        }
        return ActivityExtractor(config)
    
    @pytest.fixture
    def sample_xaml(self):
        """Create sample XAML element for testing."""
        xaml_text = '''
        <Activity x:Class="TestWorkflow" xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
                  xmlns:sap2010="http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation"
                  xmlns:ui="http://schemas.uipath.com/workflow/activities">
          <Sequence DisplayName="Main Sequence" sap2010:Annotation.AnnotationText="Main workflow sequence">
            <ui:LogMessage DisplayName="Log Start" Level="Info" Message="[&quot;Starting workflow&quot;]" />
            <ui:NClick DisplayName="Click Button" ActivateBefore="True" ClickType="Single"
                       sap2010:Annotation.AnnotationText="Click the submit button">
              <ui:NClick.Target>
                <ui:Target>
                  <ui:FullSelector><![CDATA[<webctrl id='submitBtn' tag='BUTTON' />]]></ui:FullSelector>
                </ui:Target>
              </ui:NClick.Target>
            </ui:NClick>
            <ui:ForEach TypeArgument="x:String" Values="[characterList]" DisplayName="Process Characters">
              <ActivityAction x:TypeArguments="x:String">
                <ActivityAction.Argument>
                  <DelegateInArgument x:TypeArguments="x:String" Name="currentItem" />
                </ActivityAction.Argument>
                <ui:LogMessage DisplayName="Log Character" Message="[string.Format(&quot;Processing: {0}&quot;, currentItem)]" />
              </ActivityAction>
            </ui:ForEach>
          </Sequence>
        </Activity>
        '''
        return ET.fromstring(xaml_text)
    
    @pytest.fixture
    def namespaces(self):
        """Standard UiPath XAML namespaces."""
        return {
            'x': 'http://schemas.microsoft.com/winfx/2006/xaml',
            'sap2010': 'http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation',
            'ui': 'http://schemas.uipath.com/workflow/activities'
        }
    
    def test_extract_activity_instances_basic(self, extractor, sample_xaml, namespaces):
        """Test basic activity instances extraction."""
        workflow_id = "TestWorkflow"
        project_id = "test-proj-12345678"
        
        activities = extractor.extract_activity_instances(
            sample_xaml, namespaces, workflow_id, project_id
        )
        
        # Should extract visible activities: Sequence, LogMessage, NClick, ForEach, LogMessage
        assert len(activities) >= 4
        
        # Verify all activities are Activity objects
        for activity in activities:
            assert isinstance(activity, Activity)
            assert activity.workflow_id == workflow_id
            assert activity.activity_id.startswith(project_id)
            assert '#' in activity.activity_id  # Should contain project#workflow#node#hash format
    
    def test_extract_nclick_activity_business_logic(self, extractor, sample_xaml, namespaces):
        """Test complete business logic extraction for NClick activity."""
        activities = extractor.extract_activity_instances(
            sample_xaml, namespaces, "TestWorkflow", "test-proj"
        )
        
        # Find NClick activity
        nclick_activity = None
        for activity in activities:
            if activity.activity_type == 'NClick':
                nclick_activity = activity
                break
        
        assert nclick_activity is not None, "NClick activity not found"
        
        # Verify core identification
        assert nclick_activity.activity_type == 'NClick'
        assert nclick_activity.display_name == 'Click Button'
        assert nclick_activity.annotation == 'Click the submit button'
        
        # Verify business logic extraction
        assert nclick_activity.arguments['ActivateBefore'] == 'True'
        assert nclick_activity.arguments['ClickType'] == 'Single'
        
        # Verify properties extraction
        assert nclick_activity.properties['DisplayName'] == 'Click Button'
        assert nclick_activity.properties['ActivateBefore'] == 'True'
        
        # Verify nested configuration extraction - check for the actual nested structure
        assert 'NClick.Target' in nclick_activity.configuration or 'Target' in nclick_activity.configuration
        
        # Verify selector extraction 
        assert len(nclick_activity.selectors) > 0
        # Should find FullSelector from Target configuration
        selector_found = any('FullSelector' in key for key in nclick_activity.selectors.keys())
        assert selector_found, f"FullSelector not found in selectors: {nclick_activity.selectors}"
    
    def test_extract_foreach_activity_business_logic(self, extractor, sample_xaml, namespaces):
        """Test complete business logic extraction for ForEach activity."""
        activities = extractor.extract_activity_instances(
            sample_xaml, namespaces, "TestWorkflow", "test-proj"
        )
        
        # Find ForEach activity
        foreach_activity = None
        for activity in activities:
            if activity.activity_type == 'ForEach':
                foreach_activity = activity
                break
        
        assert foreach_activity is not None, "ForEach activity not found"
        
        # Verify business logic extraction
        assert foreach_activity.arguments['Values'] == '[characterList]'
        assert foreach_activity.display_name == 'Process Characters'
        
        # Verify expressions extraction
        assert '[characterList]' in foreach_activity.expressions or 'characterList' in foreach_activity.expressions
        
        # Verify variable references
        assert 'characterList' in foreach_activity.variables_referenced
    
    def test_extract_expressions_and_variables(self, extractor, sample_xaml, namespaces):
        """Test expression and variable extraction from activities."""
        activities = extractor.extract_activity_instances(
            sample_xaml, namespaces, "TestWorkflow", "test-proj"
        )
        
        # Find LogMessage with expression
        log_activity = None
        for activity in activities:
            if (activity.activity_type == 'LogMessage' and 
                activity.display_name == 'Log Character'):
                log_activity = activity
                break
        
        assert log_activity is not None, "Log Character activity not found"
        
        # Should extract string.Format expression
        expressions_found = any('string.Format' in expr for expr in log_activity.expressions)
        assert expressions_found, f"string.Format expression not found in: {log_activity.expressions}"
        
        # Should extract currentItem variable reference
        assert 'currentItem' in log_activity.variables_referenced
    
    def test_activity_hierarchy_and_depth(self, extractor, sample_xaml, namespaces):
        """Test activity hierarchy and depth calculation."""
        activities = extractor.extract_activity_instances(
            sample_xaml, namespaces, "TestWorkflow", "test-proj"
        )
        
        # Find sequence (should be depth 0)
        sequence = None
        for activity in activities:
            if activity.activity_type == 'Sequence':
                sequence = activity
                break
        
        assert sequence is not None
        assert sequence.depth == 0
        assert sequence.parent_activity_id is None
        
        # Find child activities (should have sequence as parent and depth > 0)
        child_activities = [a for a in activities if a.parent_activity_id == sequence.activity_id]
        assert len(child_activities) > 0
        
        for child in child_activities:
            assert child.depth > 0
            assert child.parent_activity_id == sequence.activity_id
    
    def test_activity_id_uniqueness_and_format(self, extractor, sample_xaml, namespaces):
        """Test activity ID uniqueness and format compliance."""
        activities = extractor.extract_activity_instances(
            sample_xaml, namespaces, "TestWorkflow", "test-proj-12345678"
        )
        
        activity_ids = [activity.activity_id for activity in activities]
        
        # All IDs should be unique
        assert len(activity_ids) == len(set(activity_ids))
        
        # All IDs should follow format: {projectId}#{workflowId}#{nodeId}#{contentHash}
        for activity_id in activity_ids:
            parts = activity_id.split('#')
            assert len(parts) == 4, f"Invalid activity ID format: {activity_id}"
            assert parts[0] == "test-proj-12345678"  # project ID
            assert parts[1] == "TestWorkflow"  # workflow ID
            assert len(parts[2]) > 0  # node ID should not be empty
            assert len(parts[3]) == 8  # content hash should be 8 characters
            assert all(c in '0123456789abcdef' for c in parts[3])  # Should be hex
    
    def test_visibility_filtering(self, extractor, namespaces):
        """Test that only visible activities are extracted."""
        # Create XAML with invisible metadata elements
        xaml_with_metadata = '''
        <Activity xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
                  xmlns:ui="http://schemas.uipath.com/workflow/activities"
                  xmlns:sap="http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation">
          <x:Members>
            <x:Property Name="argument1" Type="InArgument(x:String)" />
          </x:Members>
          <Sequence DisplayName="Main Sequence">
            <ui:LogMessage DisplayName="Visible Log" Message="Test" />
            <sap:ViewStateService.ViewState>
              <ui:ViewStateData />
            </sap:ViewStateService.ViewState>
          </Sequence>
        </Activity>
        '''
        root = ET.fromstring(xaml_with_metadata)
        
        activities = extractor.extract_activity_instances(
            root, namespaces, "TestWorkflow", "test-proj"
        )
        
        # Should only extract visible activities (Sequence, LogMessage)
        # Should not extract metadata elements (Members, Property, ViewStateData)
        activity_types = [activity.activity_type for activity in activities]
        
        assert 'Sequence' in activity_types
        assert 'LogMessage' in activity_types
        assert 'Members' not in activity_types
        assert 'Property' not in activity_types
        assert 'ViewStateData' not in activity_types


class TestActivityExtractionIntegration:
    """Integration tests for complete activity extraction workflow."""
    
    def test_full_extraction_workflow(self):
        """Test complete extraction workflow from XAML to Activity instances."""
        # Create a realistic UiPath activity
        xaml_content = '''
        <Activity xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
                  xmlns:ui="http://schemas.uipath.com/workflow/activities"
                  xmlns:sap2010="http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation">
          <Sequence DisplayName="E-mail Processing" 
                    sap2010:Annotation.AnnotationText="Process incoming emails">
            <ui:GetIMAPMailMessages DisplayName="Get Emails" 
                                    Server="[in_Config(&quot;EmailServer&quot;).ToString]"
                                    Port="993"
                                    SecureConnection="True"
                                    Username="[in_Config(&quot;EmailUsername&quot;).ToString]"
                                    Messages="[emailList]">
              <ui:GetIMAPMailMessages.AuthenticationTypePassword>
                <ui:AuthenticationTypePassword Password="[in_Config(&quot;EmailPassword&quot;).ToString]" />
              </ui:GetIMAPMailMessages.AuthenticationTypePassword>
            </ui:GetIMAPMailMessages>
            
            <ui:ForEach TypeArgument="ui:MailMessage" Values="[emailList]" 
                        DisplayName="Process Each Email">
              <ActivityAction x:TypeArguments="ui:MailMessage">
                <ActivityAction.Argument>
                  <DelegateInArgument x:TypeArguments="ui:MailMessage" Name="currentEmail" />
                </ActivityAction.Argument>
                <ui:LogMessage DisplayName="Log Email Subject" 
                               Level="Info"
                               Message="[string.Format(&quot;Processing email: {0}&quot;, currentEmail.Subject)]" />
              </ActivityAction>
            </ui:ForEach>
          </Sequence>
        </Activity>
        '''
        
        root = ET.fromstring(xaml_content)
        namespaces = {
            'x': 'http://schemas.microsoft.com/winfx/2006/xaml',
            'ui': 'http://schemas.uipath.com/workflow/activities',
            'sap2010': 'http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation'
        }
        
        extractor = ActivityExtractor({'extract_expressions': True})
        activities = extractor.extract_activity_instances(
            root, namespaces, "EmailProcessing", "email-proj-87654321"
        )
        
        # Validate extraction completeness
        assert len(activities) >= 4  # Sequence, GetIMAPMailMessages, ForEach, LogMessage
        
        # Find and validate GetIMAPMailMessages activity (complex business logic)
        email_activity = None
        for activity in activities:
            if activity.activity_type == 'GetIMAPMailMessages':
                email_activity = activity
                break
        
        assert email_activity is not None
        
        # Verify business logic extraction
        assert email_activity.arguments['Server'] == '[in_Config("EmailServer").ToString]'
        assert email_activity.arguments['Port'] == '993'
        assert email_activity.arguments['SecureConnection'] == 'True'
        
        # Verify expressions extraction
        server_expr_found = any('in_Config("EmailServer")' in expr for expr in email_activity.expressions)
        assert server_expr_found
        
        # Verify variable references
        assert 'in_Config' in email_activity.variables_referenced
        assert 'emailList' in email_activity.variables_referenced
        
        # Verify nested configuration - check for the actual nested structure
        assert 'GetIMAPMailMessages.AuthenticationTypePassword' in email_activity.configuration or 'AuthenticationTypePassword' in email_activity.configuration
        
        # Verify activity ID format
        activity_id_parts = email_activity.activity_id.split('#')
        assert len(activity_id_parts) == 4
        assert activity_id_parts[0] == "email-proj-87654321"
        assert activity_id_parts[1] == "EmailProcessing"
    
    def test_serialization_compatibility(self):
        """Test that Activity instances can be serialized for JSON artifacts."""
        # Create simple activity
        activity = Activity(
            activity_id="proj#workflow#node#hash1234",
            workflow_id="TestWorkflow", 
            activity_type="LogMessage",
            display_name="Test Log",
            node_id="Activity/Sequence/LogMessage_1",
            depth=1,
            arguments={"Message": "Hello World", "Level": "Info"},
            configuration={},
            properties={"Message": "Hello World"},
            metadata={"IdRef": "test_id"},
            expressions=["Hello World"],
            variables_referenced=[],
            selectors={},
            annotation="Test annotation",
            is_visible=True,
            container_type="Sequence"
        )
        
        # Should serialize to dict without errors
        activity_dict = asdict(activity)
        assert activity_dict['activity_id'] == "proj#workflow#node#hash1234"
        assert activity_dict['activity_type'] == "LogMessage"
        
        # Should serialize to JSON without errors
        json_str = json.dumps(activity_dict, ensure_ascii=False)
        assert "LogMessage" in json_str
        assert "Hello World" in json_str
        
        # Should deserialize back
        parsed_dict = json.loads(json_str)
        assert parsed_dict['activity_id'] == activity.activity_id
        assert parsed_dict['arguments']['Message'] == "Hello World"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
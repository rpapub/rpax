"""
Tests for Activity Resource Generation system.

Tests the complete flow from EnhancedActivityNode to Activity resources,
including package resolution, container parsing, and resource generation.
"""
import pytest
from pathlib import Path
from unittest.mock import Mock

from rpax.parser.activity_package_resolver import ActivityPackageResolver, PackageSourceInfo
from rpax.parser.container_info_parser import ContainerInfoParser, ContainerInfo
from rpax.parser.activity_resource_generator import ActivityResourceGenerator
from rpax.parser.enhanced_xaml_analyzer import EnhancedActivityNode
from rpax.parser.dependency_classifier import DependencyInfo, DependencyType, DependencyClassifier
from rpax.resources.uri_resolver import ResourceUriResolver


class TestActivityPackageResolver:
    """Test activity type to package mapping."""
    
    def setup_method(self):
        """Set up test dependencies and classifier."""
        self.dependencies = [
            DependencyInfo(
                name="UiPath.System.Activities",
                version="23.10.3",
                classification=DependencyType.VENDOR_OFFICIAL,
                confidence=0.95,
                reasoning="Matches UiPath.* namespace pattern"
            ),
            DependencyInfo(
                name="Custom.Library", 
                version="1.0.0",
                classification=DependencyType.CUSTOM_LOCAL,
                confidence=0.85,
                reasoning="Local project library"
            ),
            DependencyInfo(
                name="UiPath.UIAutomation.Activities",
                version="23.10.0",
                classification=DependencyType.VENDOR_OFFICIAL,
                confidence=0.95,
                reasoning="Matches UiPath.* namespace pattern"
            )
        ]
        
        self.classifier = Mock(spec=DependencyClassifier)
        self.resolver = ActivityPackageResolver(self.dependencies, self.classifier)
    
    def test_resolve_known_system_activity(self):
        """Test resolving known system activity types."""
        result = self.resolver.resolve_activity_package("Assign")
        
        assert result is not None
        assert result.package_name == "UiPath.System.Activities"
        assert result.package_version == "23.10.3"
        assert result.classification == "vendor_official"
        assert result.assembly == "UiPath.Core.Activities.dll"
    
    def test_resolve_ui_automation_activity(self):
        """Test resolving UI automation activity types."""
        result = self.resolver.resolve_activity_package("Click")
        
        assert result is not None
        assert result.package_name == "UiPath.UIAutomation.Activities"
        assert result.package_version == "23.10.0"
        assert result.classification == "vendor_official"
        assert result.assembly == "UiPath.UIAutomation.Activities.dll"
    
    def test_resolve_unknown_activity(self):
        """Test resolving unknown activity types."""
        result = self.resolver.resolve_activity_package("UnknownActivity")
        
        assert result is None
    
    def test_infer_custom_activity_package(self):
        """Test inferring package from custom activity naming patterns."""
        result = self.resolver.resolve_activity_package("Custom.Library.DoSomething")
        
        assert result is not None
        assert result.package_name == "Custom.Library"
        assert result.package_version == "1.0.0"
        assert result.classification == "custom_local"
    
    def test_get_package_activity_catalog(self):
        """Test getting all activities provided by a package."""
        activities = self.resolver.get_package_activity_catalog("UiPath.System.Activities")
        
        assert "Assign" in activities
        assert "InvokeWorkflowFile" in activities
        assert "LogMessage" in activities
        assert "Sequence" in activities
        assert len(activities) > 10  # Should have many activities
    
    def test_get_all_packages(self):
        """Test getting all packages that provide activities."""
        packages = self.resolver.get_all_packages()
        
        assert "UiPath.System.Activities" in packages
        assert "UiPath.UIAutomation.Activities" in packages
        assert "Custom.Library" in packages


class TestContainerInfoParser:
    """Test container relationship parsing."""
    
    def setup_method(self):
        """Set up test activities."""
        self.parser = ContainerInfoParser()
        
        # Mock activity hierarchy: Sequence -> If -> Then/Else -> Assign
        self.activities = [
            EnhancedActivityNode(
                node_id="/Sequence[0]",
                tag="Sequence",
                display_name="Main Sequence",
                path="Activity/Sequence",
                depth=1,
                is_visual=True,
                attributes={},
                properties={},
                parent_id=None,
                line_number=10
            ),
            EnhancedActivityNode(
                node_id="/Sequence[0]/If[0]",
                tag="If",
                display_name="Check Condition",
                path="Activity/Sequence/If",
                depth=2,
                is_visual=True,
                attributes={},
                properties={},
                parent_id="/Sequence[0]",
                line_number=15
            ),
            EnhancedActivityNode(
                node_id="/Sequence[0]/If[0]/Then/Assign[0]",
                tag="Assign",
                display_name="Set Value",
                path="Activity/Sequence/If/Then/Assign",
                depth=4,
                is_visual=True,
                attributes={},
                properties={},
                parent_id="/Sequence[0]/If[0]",
                line_number=20
            ),
            EnhancedActivityNode(
                node_id="/Sequence[0]/If[0]/Else/LogMessage[0]",
                tag="LogMessage",
                display_name="Log Error",
                path="Activity/Sequence/If/Else/LogMessage",
                depth=4,
                is_visual=True,
                attributes={},
                properties={},
                parent_id="/Sequence[0]/If[0]",
                line_number=25
            )
        ]
    
    def test_parse_container_activity(self):
        """Test parsing container activity (Sequence)."""
        sequence = self.activities[0]  # Sequence
        info = self.parser.parse_container_info(sequence, self.activities)
        
        assert info.is_container is True
        assert info.parent_container is None  # Root container
        assert info.container_type is None    # No parent
        assert info.container_branch is None
    
    def test_parse_nested_container(self):
        """Test parsing nested container (If inside Sequence)."""
        if_activity = self.activities[1]  # If
        info = self.parser.parse_container_info(if_activity, self.activities)
        
        assert info.is_container is True
        assert info.parent_container == "/Sequence[0]"
        assert info.container_type == "Sequence"
        assert info.container_branch is None
    
    def test_parse_branch_activity(self):
        """Test parsing activity in Then branch."""
        then_assign = self.activities[2]  # Then/Assign
        info = self.parser.parse_container_info(then_assign, self.activities)
        
        assert info.is_container is False
        assert info.parent_container == "/Sequence[0]/If[0]"
        assert info.container_type == "If"
        assert info.container_branch == "Then"
    
    def test_parse_else_branch_activity(self):
        """Test parsing activity in Else branch."""
        else_log = self.activities[3]  # Else/LogMessage
        info = self.parser.parse_container_info(else_log, self.activities)
        
        assert info.is_container is False
        assert info.parent_container == "/Sequence[0]/If[0]"
        assert info.container_type == "If"
        assert info.container_branch == "Else"
    
    def test_build_container_hierarchy(self):
        """Test building complete container hierarchy."""
        hierarchy = self.parser.build_container_hierarchy(self.activities)
        
        # Sequence should have If as child
        assert "/Sequence[0]" in hierarchy
        assert "/Sequence[0]/If[0]" in hierarchy["/Sequence[0]"]
        
        # If should have Then/Assign and Else/LogMessage as children
        assert "/Sequence[0]/If[0]" in hierarchy
        assert "/Sequence[0]/If[0]/Then/Assign[0]" in hierarchy["/Sequence[0]/If[0]"]
        assert "/Sequence[0]/If[0]/Else/LogMessage[0]" in hierarchy["/Sequence[0]/If[0]"]
    
    def test_organize_by_branches(self):
        """Test organizing activities by branches."""
        if_activity = self.activities[1]  # If container
        branches = self.parser.organize_by_branches(if_activity.node_id, self.activities)
        
        assert "Then" in branches
        assert "Else" in branches
        assert "/Sequence[0]/If[0]/Then/Assign[0]" in branches["Then"]
        assert "/Sequence[0]/If[0]/Else/LogMessage[0]" in branches["Else"]


class TestActivityResourceGenerator:
    """Test complete activity resource generation."""
    
    def setup_method(self):
        """Set up test environment."""
        self.output_dir = Path("/tmp/test-rpax")
        self.lake_root = self.output_dir.parent
        self.uri_resolver = ResourceUriResolver(self.lake_root, "test-lake")
        self.generator = ActivityResourceGenerator(self.output_dir, self.uri_resolver)
        
        # Set up dependencies and resolver
        self.dependencies = [
            DependencyInfo(
                name="UiPath.System.Activities",
                version="23.10.3", 
                classification=DependencyType.VENDOR_OFFICIAL,
                confidence=0.95,
                reasoning="Matches UiPath.* namespace pattern"
            )
        ]
        
        self.classifier = Mock(spec=DependencyClassifier)
        self.package_resolver = ActivityPackageResolver(self.dependencies, self.classifier)
        
        # Sample activity
        self.activity = EnhancedActivityNode(
            node_id="/Sequence[0]/Assign[0]",
            tag="Assign",
            display_name="Set Configuration Path",
            path="Activity/Sequence/Assign",
            depth=2,
            is_visual=True,
            attributes={},
            properties={
                "To": {
                    "value": "[configPath]",
                    "is_expression": True
                },
                "Value": {
                    "value": "[Path.Combine(Environment.CurrentDirectory, \"Config.xlsx\")]",
                    "is_expression": True
                }
            },
            parent_id="/Sequence[0]",
            line_number=67
        )
        
        self.all_activities = [
            EnhancedActivityNode(
                node_id="/Sequence[0]",
                tag="Sequence",
                display_name="Main Sequence",
                path="Activity/Sequence",
                depth=1,
                is_visual=True,
                attributes={},
                properties={},
                parent_id=None,
                line_number=10
            ),
            self.activity
        ]
    
    def test_generate_activity_resource(self):
        """Test generating complete activity resource."""
        resource = self.generator.generate_activity_resource(
            self.activity, "Main.xaml", "calc-f4aa", 
            self.all_activities, self.package_resolver
        )
        
        # Validate activity_info
        assert resource["activity_info"]["node_id"] == "/Sequence[0]/Assign[0]"
        assert resource["activity_info"]["activity_type"] == "Assign"
        assert resource["activity_info"]["display_name"] == "Set Configuration Path"
        assert resource["activity_info"]["depth"] == 2
        assert resource["activity_info"]["line_number"] == 67
        
        # Validate package_source
        assert resource["package_source"]["package_name"] == "UiPath.System.Activities"
        assert resource["package_source"]["package_version"] == "23.10.3"
        assert resource["package_source"]["classification"] == "vendor_official"
        assert resource["package_source"]["assembly"] == "UiPath.Core.Activities.dll"
        
        # Validate properties (preserved from EnhancedActivityNode)
        assert resource["properties"]["To"]["value"] == "[configPath]"
        assert resource["properties"]["To"]["is_expression"] is True
        assert resource["properties"]["Value"]["is_expression"] is True
        
        # Validate container_info
        assert resource["container_info"]["parent_container"] == "/Sequence[0]"
        assert resource["container_info"]["container_type"] == "Sequence"
        assert resource["container_info"]["is_container"] is False
        
        # Validate relationships
        assert "rpax://test-lake/" in resource["relationships"]["workflow_uri"]
        assert "rpax://test-lake/" in resource["relationships"]["package_uri"]
    
    def test_generate_activity_collection(self):
        """Test generating activity collection for a workflow."""
        collection = self.generator.generate_activity_collection(
            self.all_activities, "calc-f4aa", "Main.xaml", self.package_resolver
        )
        
        # Validate collection_info
        assert collection["collection_info"]["workflow_name"] == "Main.xaml"
        assert collection["collection_info"]["project_slug"] == "calc-f4aa"
        assert collection["collection_info"]["total_activities"] == 2
        assert collection["collection_info"]["visual_activities"] == 2
        assert collection["collection_info"]["container_activities"] == 1
        
        # Validate statistics
        assert collection["statistics"]["activity_type_counts"]["Sequence"] == 1
        assert collection["statistics"]["activity_type_counts"]["Assign"] == 1
        assert collection["statistics"]["max_depth"] == 2
        
        # Validate activities list
        assert len(collection["activities"]) == 2
        activity_types = [a["activity_type"] for a in collection["activities"]]
        assert "Sequence" in activity_types
        assert "Assign" in activity_types
    
    def test_generate_activity_id(self):
        """Test generating safe activity IDs from node_ids."""
        test_cases = [
            ("/Sequence[0]/Assign[0]", "sequence0-assign0"),
            ("/Sequence[0]/If[1]/Then/Assign[0]", "sequence0-if1-then-assign0"),
            ("/Sequence[0]/TryCatch[0]/Catch/LogMessage[0]", "sequence0-trycatch0-catch-logmessage0")
        ]
        
        for node_id, expected_id in test_cases:
            actual_id = self.generator._generate_activity_id(node_id)
            assert actual_id == expected_id
    
    def test_generate_activities_by_package(self):
        """Test generating activity collection filtered by package."""
        collection = self.generator.generate_activities_by_package(
            self.all_activities, "calc-f4aa", "UiPath.System.Activities", self.package_resolver
        )
        
        # Should include both Sequence and Assign (both from UiPath.System.Activities)
        assert collection["package_info"]["package_name"] == "UiPath.System.Activities"
        assert collection["package_info"]["total_activities"] == 2
        
        # Validate activity types
        assert collection["statistics"]["activity_type_counts"]["Sequence"] == 1
        assert collection["statistics"]["activity_type_counts"]["Assign"] == 1


class TestIntegrationFlow:
    """Integration tests for the complete activity resource generation flow."""
    
    def test_end_to_end_activity_resource_generation(self):
        """Test complete flow from EnhancedActivityNode to Activity resource."""
        # Set up complete test environment
        output_dir = Path("/tmp/test-integration")
        uri_resolver = ResourceUriResolver(output_dir.parent, "integration-test")
        
        dependencies = [
            DependencyInfo(
                name="UiPath.System.Activities", 
                version="23.10.3", 
                classification=DependencyType.VENDOR_OFFICIAL,
                confidence=0.95,
                reasoning="Matches UiPath.* namespace pattern"
            ),
            DependencyInfo(
                name="UiPath.UIAutomation.Activities", 
                version="23.10.0", 
                classification=DependencyType.VENDOR_OFFICIAL,
                confidence=0.95,
                reasoning="Matches UiPath.* namespace pattern"
            )
        ]
        
        classifier = Mock(spec=DependencyClassifier)
        package_resolver = ActivityPackageResolver(dependencies, classifier)
        generator = ActivityResourceGenerator(output_dir, uri_resolver)
        
        # Create complex activity hierarchy
        activities = [
            EnhancedActivityNode(
                node_id="/Sequence[0]",
                tag="Sequence", 
                display_name="Main Flow",
                path="Activity/Sequence",
                depth=1,
                is_visual=True,
                attributes={},
                properties={},
                parent_id=None,
                line_number=5
            ),
            EnhancedActivityNode(
                node_id="/Sequence[0]/If[0]",
                tag="If",
                display_name="Check File Exists", 
                path="Activity/Sequence/If",
                depth=2,
                is_visual=True,
                attributes={},
                properties={"Condition": {"value": "[File.Exists(filePath)]", "is_expression": True}},
                parent_id="/Sequence[0]",
                line_number=10
            ),
            EnhancedActivityNode(
                node_id="/Sequence[0]/If[0]/Then/Click[0]",
                tag="Click",
                display_name="Click Button",
                path="Activity/Sequence/If/Then/Click", 
                depth=4,
                is_visual=True,
                attributes={},
                properties={"Target": {"value": "btnSubmit", "is_expression": False}},
                parent_id="/Sequence[0]/If[0]",
                line_number=15
            )
        ]
        
        # Generate resources for each activity
        resources = []
        for activity in activities:
            resource = generator.generate_activity_resource(
                activity, "TestWorkflow.xaml", "test-project",
                activities, package_resolver
            )
            resources.append(resource)
        
        # Validate that all resources were generated correctly
        assert len(resources) == 3
        
        # Validate Sequence resource
        sequence_resource = resources[0]
        assert sequence_resource["activity_info"]["activity_type"] == "Sequence"
        assert sequence_resource["package_source"]["package_name"] == "UiPath.System.Activities"
        assert sequence_resource["container_info"]["is_container"] is True
        
        # Validate If resource  
        if_resource = resources[1]
        assert if_resource["activity_info"]["activity_type"] == "If"
        assert if_resource["container_info"]["parent_container"] == "/Sequence[0]"
        assert if_resource["container_info"]["container_type"] == "Sequence"
        assert if_resource["container_info"]["is_container"] is True
        
        # Validate Click resource
        click_resource = resources[2]
        assert click_resource["activity_info"]["activity_type"] == "Click"
        assert click_resource["package_source"]["package_name"] == "UiPath.UIAutomation.Activities"
        assert click_resource["container_info"]["parent_container"] == "/Sequence[0]/If[0]"
        assert click_resource["container_info"]["container_branch"] == "Then"
        assert click_resource["container_info"]["is_container"] is False
        
        # Validate cross-references work
        for resource in resources:
            assert "rpax://integration-test/" in resource["relationships"]["workflow_uri"]
            assert resource["relationships"]["package_uri"] is not None
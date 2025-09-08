"""Tests for UiPath dependency classification system."""

import pytest
from pathlib import Path
from rpax.parser.dependency_classifier import (
    DependencyClassifier,
    DependencyType,
    DependencyMappingCache
)


class TestDependencyClassifier:
    """Test dependency classification with real UiPath project data."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.lake_root = Path("D:/github.com/rpapub")
        self.classifier = DependencyClassifier(self.lake_root)
    
    def test_vendor_official_classification(self):
        """Test classification of official UiPath packages."""
        test_cases = [
            ("UiPath.Excel.Activities", "[2.23.3-preview]"),
            ("UiPath.System.Activities", "24.5.0-preview"),
            ("UiPath.Testing.Activities", "[24.4.0-preview]"),
            ("UiPath.UIAutomation.Activities.Runtime", "24.4.2-preview"),
            ("UiPath.CodedWorkflows", "[24.4.2]"),
        ]
        
        for name, version in test_cases:
            dep_info = self.classifier.classify_dependency(name, version)
            assert dep_info.classification == DependencyType.VENDOR_OFFICIAL
            assert dep_info.confidence >= 0.9
            assert "vendor pattern" in dep_info.reasoning.lower()
    
    def test_custom_local_classification(self):
        """Test classification of custom local libraries."""
        # These should be classified as custom based on naming patterns
        test_cases = [
            ("LuckyLawrencium", "0.2.0"),  # Real custom library from test data
            ("FrozenChlorine", "0.2.170780471"),  # Another real custom library
        ]
        
        for name, version in test_cases:
            dep_info = self.classifier.classify_dependency(name, version)
            # Should classify as custom_local or ambiguous, not vendor
            assert dep_info.classification in [DependencyType.CUSTOM_LOCAL, DependencyType.AMBIGUOUS]
            assert dep_info.classification != DependencyType.VENDOR_OFFICIAL
    
    def test_potential_local_path_discovery(self):
        """Test discovery of potential filesystem paths for custom dependencies."""
        # Test with LuckyLawrencium which should exist in test corpus
        dep_info = self.classifier.classify_dependency("LuckyLawrencium", "0.2.0")
        
        # If the test corpus is available, should find potential paths
        if self.lake_root.exists():
            # May find paths or may not, depending on test environment
            # But should not crash and should be properly structured
            assert isinstance(dep_info.potential_local_paths, list)
            for path in dep_info.potential_local_paths:
                assert isinstance(path, Path)
    
    def test_project_dependencies_classification(self):
        """Test classification of full project dependency sets."""
        # Real dependencies from FrozenChlorine project
        dependencies = {
            "LuckyLawrencium": "0.2.0",
            "UiPath.CodedWorkflows": "[24.4.2]",
            "UiPath.Excel.Activities": "[2.23.3-preview]",
            "UiPath.System.Activities.Runtime": "24.5.0-preview",
            "UiPath.Testing.Activities": "[24.4.0-preview]",
            "UiPath.UIAutomation.Activities.Runtime": "24.4.2-preview"
        }
        
        classified = self.classifier.classify_project_dependencies(dependencies)
        
        assert len(classified) == 6
        
        # Check that UiPath packages are classified as vendor
        uipath_deps = [d for d in classified if d.name.startswith("UiPath.")]
        for dep in uipath_deps:
            assert dep.classification == DependencyType.VENDOR_OFFICIAL
        
        # Check that LuckyLawrencium is not classified as vendor
        lucky_dep = next(d for d in classified if d.name == "LuckyLawrencium")
        assert lucky_dep.classification != DependencyType.VENDOR_OFFICIAL
    
    def test_mcp_classification_requests(self):
        """Test generation of MCP requests for ambiguous dependencies."""
        # Create some ambiguous dependencies
        dependencies = {
            "SomeAmbiguousPackage": "1.0.0",
            "UiPath.Excel.Activities": "[2.23.3]",  # Should not generate request
        }
        
        classified = self.classifier.classify_project_dependencies(dependencies)
        mcp_requests = self.classifier.get_mcp_classification_requests(classified)
        
        # Should only generate requests for ambiguous dependencies
        ambiguous_deps = [d for d in classified if d.classification == DependencyType.AMBIGUOUS]
        assert len(mcp_requests) == len(ambiguous_deps)
        
        if mcp_requests:
            request = mcp_requests[0]
            assert "type" in request
            assert "package_name" in request
            assert "suggested_classifications" in request
            assert "question" in request
    
    def test_cache_integration(self):
        """Test MCP cache integration for learned mappings."""
        # Create classifier with cache
        cache = DependencyMappingCache()
        classifier = DependencyClassifier(self.lake_root, cache)
        
        # Provide user classification via MCP
        classifier.update_cache_from_mcp(
            "CustomLibrary",
            DependencyType.CUSTOM_LOCAL,
            filesystem_path="/path/to/custom/lib",
            confidence=1.0
        )
        
        # Should use cached classification
        dep_info = classifier.classify_dependency("CustomLibrary", "1.0.0")
        assert dep_info.classification == DependencyType.CUSTOM_LOCAL
        assert dep_info.confidence == 1.0
        assert dep_info.user_provided_mapping == "/path/to/custom/lib"
        assert "User/LLM provided" in dep_info.reasoning
    
    def test_classification_summary_export(self):
        """Test export of classification summary for MCP/API consumption."""
        dependencies = {
            "UiPath.Excel.Activities": "[2.23.3]",
            "LuckyLawrencium": "0.2.0",
            "AmbiguousPackage": "1.0.0"
        }
        
        classified = self.classifier.classify_project_dependencies(dependencies)
        summary = self.classifier.export_classification_summary(classified)
        
        assert "total_dependencies" in summary
        assert "by_classification" in summary
        assert "high_confidence" in summary
        assert "requires_assistance" in summary
        assert "local_mappings" in summary
        
        assert summary["total_dependencies"] == 3
        
        # Should have at least one vendor official (UiPath.Excel.Activities)
        assert summary["by_classification"].get(DependencyType.VENDOR_OFFICIAL.value, 0) >= 1
    
    def test_project_name_sanitization(self):
        """Test UiPath Studio package name conversion logic."""
        test_cases = [
            ("BlankLibrary1", "BlankLibrary1"),  # No change
            ("Blank Library_1-0", "Blank.Library_1-0"),  # Spaces to dots
            ("Blank Library_1-0 äöü", "Blank.Library_1-0.äöü"),  # Spaces to dots, special chars preserved
            ("Test Library With Spaces", "Test.Library.With.Spaces"),  # All spaces to dots
            ("A B C D E", "A.B.C.D.E"),  # Each space to dot
            ("My_Test-Library.v2", "My_Test-Library.v2"),  # Underscores, dashes, dots preserved
            ("CamelCaseLibrary", "CamelCaseLibrary"),  # No spaces, no change
        ]
        
        for input_name, expected_output in test_cases:
            sanitized = self.classifier._sanitize_project_name(input_name)
            assert sanitized == expected_output, f"Expected '{expected_output}' but got '{sanitized}' for input '{input_name}'"


@pytest.mark.integration
class TestDependencyClassifierIntegration:
    """Integration tests with real UiPath test corpus."""
    
    def setup_method(self):
        """Setup with real test corpus paths."""
        self.test_corpus_paths = [
            Path("D:/github.com/rpapub/rpax-corpuses/c25v001_CORE_00000001/project.json"),
            Path("D:/github.com/rpapub/FrozenChlorine/project.json"), 
            Path("D:/github.com/rpapub/LuckyLawrencium/project.json"),
        ]
        self.lake_root = Path("D:/github.com/rpapub")
        self.classifier = DependencyClassifier(self.lake_root)
    
    def test_real_project_classification(self):
        """Test classification on real UiPath projects."""
        import json
        
        for project_path in self.test_corpus_paths:
            if not project_path.exists():
                pytest.skip(f"Test corpus not available: {project_path}")
            
            with open(project_path) as f:
                project_data = json.load(f)
            
            dependencies = project_data.get("dependencies", {})
            if not dependencies:
                continue  # Skip projects without dependencies
            
            classified = self.classifier.classify_project_dependencies(
                dependencies, project_path.parent
            )
            
            # Should classify all dependencies without crashing
            assert len(classified) == len(dependencies)
            
            # All should have valid classifications
            for dep in classified:
                assert isinstance(dep.classification, DependencyType)
                assert 0.0 <= dep.confidence <= 1.0
                assert dep.reasoning  # Should have reasoning
            
            # Generate summary
            summary = self.classifier.export_classification_summary(classified)
            assert summary["total_dependencies"] == len(dependencies)
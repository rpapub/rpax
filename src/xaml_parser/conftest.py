"""Pytest configuration and fixtures for XAML parser tests."""

import pytest
from pathlib import Path

from xaml_parser import XamlParser


@pytest.fixture
def parser():
    """Basic parser fixture."""
    return XamlParser()


@pytest.fixture
def strict_parser():
    """Parser with strict mode enabled."""
    return XamlParser({'strict_mode': True})


@pytest.fixture
def test_xaml():
    """Sample XAML content for testing."""
    return """<?xml version="1.0" encoding="utf-8"?>
<Activity x:Class="Main" xmlns="http://schemas.microsoft.com/netfx/2009/xaml/activities" xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml" xmlns:sap2010="http://schemas.microsoft.com/netfx/2010/xaml/activities/presentation">
  <x:Members>
    <x:Property Name="in_TestArg" Type="InArgument(x:String)" sap2010:Annotation.AnnotationText="Test argument" />
  </x:Members>
  <Sequence DisplayName="Test Sequence" sap2010:Annotation.AnnotationText="Test workflow">
    <LogMessage DisplayName="Log Test" Text="Hello World" />
  </Sequence>
</Activity>"""


@pytest.fixture
def corpus_dir():
    """Path to test corpus directory."""
    return Path(__file__).parent / "tests" / "corpus"


@pytest.fixture
def simple_project(corpus_dir):
    """Path to simple test project."""
    return corpus_dir / "simple_project"


@pytest.fixture
def main_workflow(simple_project):
    """Path to Main.xaml in simple project."""
    return simple_project / "Main.xaml"


@pytest.fixture
def corpus_available(corpus_dir):
    """Check if corpus data is available."""
    return corpus_dir.exists() and (corpus_dir / "simple_project" / "Main.xaml").exists()


def pytest_configure(config):
    """Configure pytest with custom settings."""
    config.addinivalue_line("markers", "requires_corpus: mark test as requiring corpus data")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers."""
    for item in items:
        # Mark integration tests
        if "integration" in item.nodeid.lower():
            item.add_marker(pytest.mark.integration)
        
        # Mark corpus tests
        if "corpus" in item.nodeid.lower():
            item.add_marker(pytest.mark.corpus)
            item.add_marker(pytest.mark.requires_corpus)
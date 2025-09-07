"""Simple performance benchmarks for core rpax functionality."""

import json
import tempfile
import time
from pathlib import Path

import pytest

from rpax.config import ProjectConfig, RpaxConfig, ValidationConfig
from rpax.parser.xaml import XamlDiscovery
from rpax.validation.framework import ValidationFramework


class TestSimplePerformanceBenchmarks:
    """Simple performance benchmarks for rpax components."""

    @pytest.mark.performance
    def test_workflow_discovery_performance(self):
        """Benchmark workflow discovery on medium project."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "MediumProject"
            project_dir.mkdir()

            # Create project.json
            project_json = {
                "name": "MediumProject",
                "main": "Main.xaml",
                "dependencies": {},
                "entryPoints": [{"filePath": "Main.xaml", "uniqueId": "main"}]
            }
            (project_dir / "project.json").write_text(json.dumps(project_json))

            # Create many workflow files
            workflow_template = """<?xml version="1.0" encoding="utf-8"?>
<Activity x:Class="Workflow{index}">
  <Sequence DisplayName="Workflow {index}">
    <WriteLine Text="Workflow {index}" />
  </Sequence>
</Activity>"""

            for i in range(50):  # 50 workflows for reasonable test time
                xaml_content = workflow_template.format(index=i)
                (project_dir / f"Workflow{i}.xaml").write_text(xaml_content)

            # Benchmark discovery
            discovery = XamlDiscovery(project_dir)

            start_time = time.time()
            index = discovery.discover_workflows()
            elapsed = time.time() - start_time

            print(f"Discovery of {len(index.workflows)} workflows took {elapsed:.3f} seconds")

            # Performance assertions
            assert len(index.workflows) == 50
            assert elapsed < 5.0  # Should complete within 5 seconds
            assert elapsed / len(index.workflows) < 0.1  # < 100ms per workflow

    @pytest.mark.performance
    def test_validation_performance_with_data(self):
        """Benchmark validation framework with realistic data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            project_dir = Path(temp_dir) / "ValidationTest"
            artifacts_dir = project_dir / ".rpax-lake"
            artifacts_dir.mkdir(parents=True)

            # Create manifest
            manifest = {
                "projectName": "ValidationTest",
                "projectType": "process",
                "projectRoot": str(project_dir),
                "rpaxVersion": "0.1.0",
                "generatedAt": "2024-01-01T00:00:00Z",
                "mainWorkflow": "Main.xaml",
                "totalWorkflows": 30
            }
            (artifacts_dir / "manifest.json").write_text(json.dumps(manifest))

            # Create workflow index
            workflows = []
            for i in range(30):
                workflows.append({
                    "id": f"test#{i}#hash{i:04d}",
                    "projectSlug": "test",
                    "workflowId": f"Workflow{i}.xaml",
                    "contentHash": f"hash{i:04d}" + "0" * 60,  # Pad to 64 chars
                    "filePath": str(project_dir / f"Workflow{i}.xaml"),
                    "fileName": f"Workflow{i}.xaml",
                    "relativePath": f"Workflow{i}.xaml",
                    "discoveredAt": "2024-01-01T00:00:00Z",
                    "fileSize": 1024,
                    "lastModified": "2024-01-01T00:00:00Z"
                })

            index = {
                "projectName": "ValidationTest",
                "projectRoot": str(project_dir),
                "scanTimestamp": "2024-01-01T00:00:00Z",
                "totalWorkflows": 30,
                "successfulParses": 30,
                "failedParses": 0,
                "workflows": workflows
            }
            (artifacts_dir / "workflows.index.json").write_text(json.dumps(index))

            # Create invocations with some missing references
            invocations = []
            for i in range(30):
                if i > 0 and i % 5 != 0:
                    target_index = max(0, i - 3)
                    invocations.append({
                        "kind": "invoke",
                        "from": f"test#{i}#hash{i:04d}",
                        "to": f"test#{target_index}#hash{target_index:04d}",
                        "targetPath": f"Workflow{target_index}.xaml"
                    })

            # Add some missing references
            for i in [5, 15, 25]:
                invocations.append({
                    "kind": "invoke-missing",
                    "from": f"test#{i}#hash{i:04d}",
                    "to": f"MissingWorkflow{i}",
                    "targetPath": f"MissingWorkflow{i}.xaml"
                })

            invocations_content = "\n".join(json.dumps(inv) for inv in invocations)
            (artifacts_dir / "invocations.jsonl").write_text(invocations_content)

            # Run validation benchmark
            config = RpaxConfig(
                project=ProjectConfig(name="ValidationTest", type="process"),
                validation=ValidationConfig(failOnMissing=True, failOnCycles=True)
            )

            framework = ValidationFramework(config)

            start_time = time.time()
            result = framework.validate(artifacts_dir)
            elapsed = time.time() - start_time

            print(f"Validated project with {len(invocations)} invocations in {elapsed:.3f}s")
            print(f"Validation result: {result.status}")
            print(f"Issues: {len(result.issues)}")

            # Performance assertions
            assert elapsed < 5.0  # Should complete within 5 seconds
            assert result.status.value in ["pass", "fail", "warn"]

    @pytest.mark.performance
    def test_memory_usage_reasonable(self):
        """Test that memory usage doesn't grow excessively."""
        try:
            import os

            import psutil

            process = psutil.Process(os.getpid())
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB

            with tempfile.TemporaryDirectory() as temp_dir:
                project_dir = Path(temp_dir) / "MemoryTest"
                project_dir.mkdir()

                # Create project.json
                project_json = {
                    "name": "MemoryTest",
                    "main": "Main.xaml",
                    "dependencies": {},
                    "entryPoints": [{"filePath": "Main.xaml", "uniqueId": "main"}]
                }
                (project_dir / "project.json").write_text(json.dumps(project_json))

                # Create many workflows
                for i in range(100):
                    xaml_content = f"""<?xml version="1.0" encoding="utf-8"?>
<Activity x:Class="Workflow{i}">
  <Sequence DisplayName="Workflow {i}">
    <WriteLine Text="Processing item {i}" />
  </Sequence>
</Activity>"""
                    (project_dir / f"Workflow{i}.xaml").write_text(xaml_content)

                # Process all workflows
                discovery = XamlDiscovery(project_dir)
                index = discovery.discover_workflows()

                peak_memory = process.memory_info().rss / 1024 / 1024  # MB
                memory_growth = peak_memory - initial_memory

                print(f"Memory usage: {initial_memory:.1f} MB -> {peak_memory:.1f} MB (+{memory_growth:.1f} MB)")
                print(f"Processed {len(index.workflows)} workflows")

                # Memory growth should be reasonable
                assert memory_growth < 50  # Less than 50MB growth for 100 workflows
                assert memory_growth / len(index.workflows) < 0.5  # Less than 0.5MB per workflow

        except ImportError:
            pytest.skip("psutil not available for memory testing")

    @pytest.mark.performance
    def test_scalability_comparison(self):
        """Test how performance scales with different project sizes."""
        sizes = [10, 25, 50]
        times = []

        for size in sizes:
            with tempfile.TemporaryDirectory() as temp_dir:
                project_dir = Path(temp_dir) / f"ScaleTest{size}"
                project_dir.mkdir()

                # Create project.json
                project_json = {
                    "name": f"ScaleTest{size}",
                    "main": "Main.xaml",
                    "dependencies": {},
                    "entryPoints": [{"filePath": "Main.xaml", "uniqueId": "main"}]
                }
                (project_dir / "project.json").write_text(json.dumps(project_json))

                # Create workflows
                for i in range(size):
                    xaml_content = f"""<?xml version="1.0" encoding="utf-8"?>
<Activity x:Class="Workflow{i}">
  <Sequence DisplayName="Workflow {i}">
    <WriteLine Text="Workflow {i} processing" />
  </Sequence>
</Activity>"""
                    (project_dir / f"Workflow{i}.xaml").write_text(xaml_content)

                # Measure discovery time
                discovery = XamlDiscovery(project_dir)

                start_time = time.time()
                index = discovery.discover_workflows()
                elapsed = time.time() - start_time

                times.append(elapsed)

                print(f"Size {size}: {elapsed:.3f}s ({elapsed/size*1000:.1f}ms per workflow)")

                assert len(index.workflows) == size
                assert elapsed < size * 0.1  # Should be roughly linear or better

        # Performance should scale reasonably (not exponentially)
        # Allow some variation but ensure it's not getting dramatically worse
        for i in range(1, len(times)):
            ratio = times[i] / times[i-1]
            size_ratio = sizes[i] / sizes[i-1]
            # Time ratio should not be dramatically worse than size ratio (allow overhead for small numbers)
            assert ratio < size_ratio * 5.0, f"Performance degraded significantly at size {sizes[i]}"

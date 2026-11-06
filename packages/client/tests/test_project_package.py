from unittest.mock import MagicMock
import msgspec
from obs_flow_client import project_list, project_show, package_list, package_show
from obs_flow_common.messages import (
    ProjectListRequest,
    ProjectListResponse,
    ProjectShowRequest,
    ProjectShowResponse,
    ProjectDetail,
    PackageListRequest,
    PackageListResponse,
    PackageShowRequest,
    PackageShowResponse,
    PackageDetail,
)


def test_project_client():
    conn = MagicMock()
    # Mock project_list
    proj = ProjectDetail(id=1, name="proj1", workflow_type="direct", org="org1", branch_name="main")
    res_bytes = msgspec.json.encode(ProjectListResponse(projects=[proj]))
    conn.post.return_value = res_bytes

    req = ProjectListRequest(name="proj1")
    res = project_list(conn, req)
    assert len(res.projects) == 1
    assert res.projects[0].name == "proj1"
    conn.post.assert_called_with("/api/v1/project/list", data=msgspec.json.encode(req))

    # Mock project_show
    show_bytes = msgspec.json.encode(ProjectShowResponse(project=proj))
    conn.post.return_value = show_bytes

    show_req = ProjectShowRequest(name="proj1")
    show_res = project_show(conn, show_req)
    assert show_res.project.name == "proj1"
    conn.post.assert_called_with("/api/v1/project/show", data=msgspec.json.encode(show_req))


def test_package_client():
    conn = MagicMock()
    # Mock package_list
    pkg = PackageDetail(id=1, project="proj1", name="pkg1", forked_from=None)
    res_bytes = msgspec.json.encode(PackageListResponse(packages=[pkg]))
    conn.post.return_value = res_bytes

    req = PackageListRequest(project="proj1", name="pkg1")
    res = package_list(conn, req)
    assert len(res.packages) == 1
    assert res.packages[0].name == "pkg1"
    conn.post.assert_called_with("/api/v1/package/list", data=msgspec.json.encode(req))

    # Mock package_show
    show_bytes = msgspec.json.encode(PackageShowResponse(package=pkg))
    conn.post.return_value = show_bytes

    show_req = PackageShowRequest(project="proj1", name="pkg1")
    show_res = package_show(conn, show_req)
    assert show_res.package.name == "pkg1"
    conn.post.assert_called_with("/api/v1/package/show", data=msgspec.json.encode(show_req))

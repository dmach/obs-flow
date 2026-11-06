import msgspec
from obs_flow_common.messages import (
    ProjectListRequest,
    ProjectShowRequest,
    ProjectShowResponse,
    ProjectDetail,
    PackageListRequest,
    PackageShowRequest,
    PackageShowResponse,
    PackageDetail,
)


def test_project_messages():
    req = ProjectListRequest(name="foo", org="bar", workflow_type="direct")
    encoded = msgspec.json.encode(req)
    decoded = msgspec.json.decode(encoded, type=ProjectListRequest)
    assert decoded.name == "foo"
    assert decoded.org == "bar"
    assert decoded.workflow_type == "direct"

    show_req = ProjectShowRequest(name="my-proj")
    encoded_show = msgspec.json.encode(show_req)
    decoded_show = msgspec.json.decode(encoded_show, type=ProjectShowRequest)
    assert decoded_show.name == "my-proj"

    proj_detail = ProjectDetail(id=1, name="my-proj", workflow_type="direct", org="my-org", branch_name="main")
    show_res = ProjectShowResponse(project=proj_detail)
    encoded_res = msgspec.json.encode(show_res)
    decoded_res = msgspec.json.decode(encoded_res, type=ProjectShowResponse)
    assert decoded_res.project.id == 1
    assert decoded_res.project.name == "my-proj"


def test_package_messages():
    req = PackageListRequest(project="my-proj", name="pkg")
    encoded = msgspec.json.encode(req)
    decoded = msgspec.json.decode(encoded, type=PackageListRequest)
    assert decoded.project == "my-proj"
    assert decoded.name == "pkg"

    show_req = PackageShowRequest(project="my-proj", name="pkg")
    encoded_show = msgspec.json.encode(show_req)
    decoded_show = msgspec.json.decode(encoded_show, type=PackageShowRequest)
    assert decoded_show.project == "my-proj"
    assert decoded_show.name == "pkg"

    pkg_detail = PackageDetail(id=2, project="my-proj", name="pkg", forked_from=None)
    show_res = PackageShowResponse(package=pkg_detail)
    encoded_res = msgspec.json.encode(show_res)
    decoded_res = msgspec.json.decode(encoded_res, type=PackageShowResponse)
    assert decoded_res.package.id == 2
    assert decoded_res.package.name == "pkg"

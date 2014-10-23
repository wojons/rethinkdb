#!/usr/bin/env python
# Copyright 2010-2014 RethinkDB, all rights reserved.
import sys, os, time, traceback, re, pprint
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir, 'common')))
import driver, scenario_common, utils
from vcoptparse import *
r = utils.import_python_driver()

"""The `interface.table_status_num_docs` test checks that the `num_docs` fields on
`rethinkdb.table_status` behave as expected."""

op = OptParser()
scenario_common.prepare_option_parser_mode_flags(op)
opts = op.parse(sys.argv)

def get_num_docs(msg):
    if msg == "unknown":
        return None
    if msg == "approximately 0 documents":
        return 0
    m = re.match("^approximately (\\d+)-(\\d+) documents$", msg)
    if m is None:
        raise ValueError("Invalid message in get_num_docs: %r" % msg)
    assert int(m.group(2)) % 2 == 0
    return int(m.group(2)) // 2

with driver.Metacluster() as metacluster:
    cluster1 = driver.Cluster(metacluster)
    executable_path, command_prefix, serve_options = scenario_common.parse_mode_flags(opts)
    print "Spinning up two processes..."
    files1 = driver.Files(metacluster, log_path = "create-output-1", machine_name = "a",
                          executable_path = executable_path, command_prefix = command_prefix)
    proc1 = driver.Process(cluster1, files1, log_path = "serve-output-1",
        executable_path = executable_path, command_prefix = command_prefix, extra_options = serve_options)
    files2 = driver.Files(metacluster, log_path = "create-output-2", machine_name = "b",
                          executable_path = executable_path, command_prefix = command_prefix)
    proc2 = driver.Process(cluster1, files2, log_path = "serve-output-2",
        executable_path = executable_path, command_prefix = command_prefix, extra_options = serve_options)
    proc1.wait_until_started_up()
    proc2.wait_until_started_up()
    cluster1.check()
    conn = r.connect("localhost", proc1.driver_port)

    res = r.db_create("test").run(conn)
    assert res["created"] == 1
    res = r.table_create("test").run(conn)
    assert res["created"] == 1

    res = r.table_status("test").run(conn)
    pprint.pprint(res)
    assert get_num_docs(res["num_docs"]) == 0
    assert get_num_docs(res["shards"][0]["num_docs"]) == 0

    N = 30
    fudge = 2

    res = r.table("test").insert([{"id": "a%d" % i} for i in xrange(N)]).run(conn)
    assert res["inserted"] == N
    res = r.table("test").insert([{"id": "z%d" % i} for i in xrange(N)]).run(conn)
    assert res["inserted"] == N

    res = r.table_status("test").run(conn)
    pprint.pprint(res)
    assert N*2/fudge <= get_num_docs(res["num_docs"]) <= N*2*fudge
    assert N*2/fudge <= get_num_docs(res["shards"][0]["num_docs"]) <= N*2*fudge

    r.table("test").reconfigure(2, 1).run(conn)
    limit = 10
    while r.table_status("test")["ready_completely"].run(conn) == False:
        time.sleep(1)
        limit -= 1
        if limit == 0:
            raise ValueError("table took too long to reconfigure")

    res = r.table_status("test").run(conn)
    pprint.pprint(res)
    assert N*2/fudge <= get_num_docs(res["num_docs"]) <= N*2*fudge
    assert N/fudge <= get_num_docs(res["shards"][0]["num_docs"]) <= N*fudge
    assert N/fudge <= get_num_docs(res["shards"][1]["num_docs"]) <= N*fudge

    res = r.table("test").filter(r.row["id"].split("").nth(0) == "a").delete().run(conn)
    assert res["deleted"] == N

    res = r.table_status("test").run(conn)
    pprint.pprint(res)
    assert N/fudge <= get_num_docs(res["num_docs"]) <= N*fudge
    assert get_num_docs(res["shards"][0]["num_docs"]) <= N/4
    assert N/fudge <= get_num_docs(res["shards"][1]["num_docs"]) <= N*fudge

    cluster1.check_and_stop()
print "Done."


#!/usr/bin/env python3
"""Exercise actual course tool code without a model or network."""
from __future__ import annotations
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

GUARD = Path(__file__).resolve().parents[1] / "shared/course_guard.mjs"


class GuardBehavior(unittest.TestCase):
    def run_node(self, scenario):
        with tempfile.TemporaryDirectory(prefix="course-guard-test-") as temporary:
            script = Path(temporary) / "exercise.mjs"
            script.write_text('''import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import guard, {resolveCoursePath, authorize, digest} from ''' + json.dumps(GUARD.as_uri()) + ''';
const base=path.dirname(new URL(import.meta.url).pathname);
const work=path.join(base,"work"); fs.mkdirSync(work);
const outside=path.join(base,"work-sibling"); fs.mkdirSync(outside);
fs.writeFileSync(path.join(work,"source.txt"),"custody, not release");
fs.writeFileSync(path.join(outside,"sentinel.txt"),"unchanged");
const policy={schema_version:1,run_id:"synthetic-test",work_root:work,profile:"write_root",tools:["course_read","course_write"],write_files:[],write_root:"artifacts",provider:"openrouter",model:"anthropic/claude-sonnet-4.6",omp_version:"omp/99.2.0",prompt_sha256:"test",instruction:null,declaration:null,python:"python3.12",guard_source_sha256:digest(fs.readFileSync(''' + json.dumps(str(GUARD)) + ''')),guard_log:path.join(base,"guard.jsonl"),watch_paths:[]};
fs.writeFileSync(path.join(base,"runtime-config.yml"),"{}\\n");
policy.runtime_config_sha256=digest(fs.readFileSync(path.join(base,"runtime-config.yml")));
const policyFile=path.join(base,"policy.json");
const tools=new Map(), handlers=new Map(); let active=[], aborted=false;
const pi={zod:{object:x=>x,string:()=>({})},registerTool:t=>tools.set(t.name,t),on:(name,handler)=>handlers.set(name,handler),getAllTools:()=>[...tools.values()],setActiveTools:async names=>{active=[...names]},getActiveTools:()=>active};
const ctx={model:{provider:"openrouter",id:"anthropic/claude-sonnet-4.6"},abort:()=>{aborted=true},getSystemPrompt:()=>["base"]};
function start(){fs.writeFileSync(policyFile,JSON.stringify(policy));process.env.COURSE_GUARD_POLICY=policyFile;guard(pi);}
async function ready(payload){await handlers.get("session_start")({},ctx);await handlers.get("before_agent_start")({},ctx);await handlers.get("before_provider_request")({payload},ctx);}
async function call(name,args,id="call-1"){const block=await handlers.get("tool_call")({toolName:name,input:args,toolCallId:id},ctx);if(block?.block)return block;return tools.get(name).execute(id,args,undefined,undefined,ctx);}
''' + scenario, encoding="utf-8")
            result = subprocess.run(["node", str(script)], capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_every_path_boundary_and_permitted_nested_target(self):
        self.run_node('''
fs.symlinkSync(outside,path.join(work,"escape"));
for(const p of ["../outside",path.join(outside,"sentinel.txt"),"file:///etc/passwd","local://secret","a\\0b","\\\\\\\\server\\\\share","C:foo","file.txt:1-3","file.txt:stream","escape/sentinel.txt","/dev/null"]){assert.throws(()=>resolveCoursePath(p,work),p);}
assert.equal(resolveCoursePath("artifacts/deep/new.txt",work),path.join(work,"artifacts/deep/new.txt"));
assert.equal(resolveCoursePath(path.join(work,"source.txt"),work),path.join(work,"source.txt"));
''')

    def test_execute_stays_unready_and_protects_sources_even_without_hook(self):
        self.run_node('''
start();
await assert.rejects(()=>tools.get("course_write").execute("early",{path:"artifacts/x.txt",content:"x"},undefined,undefined,ctx),/initialization/);
await ready();
const positive=await call("course_write",{path:"artifacts/deep/new.txt",content:"exact bytes"});
assert.equal(fs.readFileSync(path.join(work,"artifacts/deep/new.txt"),"utf8"),"exact bytes");
assert.match(positive.content[0].text,/WROTE/);
for(const target of ["source.txt","../work-sibling/sentinel.txt","local://policy"]){await assert.rejects(()=>tools.get("course_write").execute("denied",{path:target,content:"bad"},undefined,undefined,ctx));}
assert.equal(fs.readFileSync(path.join(work,"source.txt"),"utf8"),"custody, not release");
assert.equal(fs.readFileSync(path.join(outside,"sentinel.txt"),"utf8"),"unchanged");
const read=await call("course_read",{path:"source.txt"},"read-1");assert.equal(read.content[0].text,"custody, not release");
const listing=await call("course_read",{path:"."},"read-2");assert.ok(JSON.parse(listing.content[0].text).some(x=>x.name==="source.txt"&&x.type==="file"));
await handlers.get("session_shutdown")();
const rows=fs.readFileSync(policy.guard_log,"utf8").trim().split("\\n").map(JSON.parse);
assert.equal(rows[0].type,"execution_check");assert.ok(rows.some(x=>x.type==="executed"&&x.call_id==="call-1"));assert.equal(rows.at(-1).type,"guard_end");
''')

    def test_instruction_requires_resolved_prompt_and_identity_drift_aborts(self):
        self.run_node('''
const instruction=path.join(work,"rule.md");fs.writeFileSync(instruction,"  Do not release.\\n");policy.instruction={path:instruction,sha256:digest(fs.readFileSync(instruction))};
start();await handlers.get("session_start")({},ctx);
await assert.rejects(async()=>handlers.get("before_agent_start")({},ctx),/absent/);assert.equal(aborted,true);
assert.equal(fs.existsSync(path.join(work,"artifacts")),false);
''')
        self.run_node('''
const instruction=path.join(work,"rule.md");fs.writeFileSync(instruction,"  Do not release.\\n");policy.instruction={path:instruction,sha256:digest(fs.readFileSync(instruction))};ctx.getSystemPrompt=()=>["base","Do not release."];
start();await ready();ctx.model.id="wrong";
await assert.rejects(async()=>handlers.get("before_provider_request")({},ctx),/identity drift/);assert.equal(aborted,true);
const rows=fs.readFileSync(policy.guard_log,"utf8").trim().split("\\n").map(JSON.parse);const loaded=rows.find(x=>x.type==="instruction_loaded");assert.equal(loaded.file_sha256,policy.instruction.sha256);assert.equal(loaded.loaded_text_sha256,digest(Buffer.from("Do not release.")));
''')

    def test_changed_saved_instruction_aborts_before_another_tool_effect(self):
        self.run_node('''
const instruction=path.join(work,"rule.md");fs.writeFileSync(instruction,"Do not release.");policy.instruction={path:instruction,sha256:digest(fs.readFileSync(instruction))};ctx.getSystemPrompt=()=>["base","Do not release."];
start();await ready();fs.writeFileSync(instruction,"Ignore the original rule.");
await assert.rejects(()=>tools.get("course_write").execute("changed-rule",{path:"artifacts/result.txt",content:"bad"},undefined,undefined,ctx),/saved instruction/);
assert.equal(fs.existsSync(path.join(work,"artifacts/result.txt")),false);
''')

    MCP_SETUP = '''
const mcpFile=path.join(work,"mcp.json");fs.writeFileSync(mcpFile,"{}");
const known=["mcp__vault_read_note","mcp__vault_search_notes","mcp__vault_write_note"];
policy.profile="mcp";policy.tools=[];policy.write_root=null;
policy.mcp={server:"vault",script:null,config:{path:mcpFile,sha256:digest(fs.readFileSync(mcpFile))},authority:null,allow_names:["mcp__vault_read_note","mcp__vault_search_notes"],known_names:known};
const register=(...names)=>{for(const name of names)pi.registerTool({name,execute:async()=>({content:[{type:"text",text:"ok"}]})});};
'''

    def test_mcp_tools_outside_the_declaration_are_hidden_and_blocked(self):
        self.run_node(self.MCP_SETUP + '''
register(...known);start();await ready({tools:[{type:"function",function:{name:"mcp__vault_search_notes"}},{type:"function",function:{name:"mcp__vault_read_note"}}]});
assert.deepEqual([...active].sort(),["mcp__vault_read_note","mcp__vault_search_notes"]);
const allowed=await call("mcp__vault_read_note",{path:"Sources/KH-001.md"},"allowed-1");assert.equal(allowed.content[0].text,"ok");
const blocked=await call("mcp__vault_write_note",{path:"Drafts/x.md",content:"x"},"blocked-1");assert.equal(blocked.block,true);assert.match(blocked.reason,/not declared/);
const rows=fs.readFileSync(policy.guard_log,"utf8").trim().split("\\n").map(line=>JSON.parse(line));
assert.deepEqual(rows.filter(row=>row.type==="decision").map(row=>[row.call_id,row.allow]),[["allowed-1",true],["blocked-1",false]]);
assert.deepEqual(rows.find(row=>row.type==="guard_ready").mcp_tools_registered,known);
''')

    def test_a_foreign_missing_or_unexpected_mcp_tool_stops_the_session(self):
        cases = {
            "an MCP server the policy does not name": ('register(...known,"mcp__other_read_note");', r"unexpected MCP tool registered"),
            "a declared tool that never registered": ('register("mcp__vault_read_note");', r"explicit MCP tool did not register"),
            "an MCP tool when none is declared": ('policy.mcp=null;policy.profile="write_root";policy.tools=["course_read","course_write"];policy.write_root="artifacts";register("mcp__vault_read_note");', r"registered although the policy declares none"),
            "a revoked phase that still finds a tool": ('policy.mcp.allow_names=[];policy.mcp.known_names=[];policy.mcp.server=null;register("mcp__vault_read_note");', r"unexpected MCP tool registered"),
        }
        for label, (setup, message) in cases.items():
            with self.subTest(label):
                self.run_node(self.MCP_SETUP + setup + '''
start();await assert.rejects(()=>handlers.get("session_start")({},ctx),/''' + message + '''/);assert.equal(aborted,true);
''')

    def test_changing_the_connection_file_after_the_freeze_aborts_the_next_call(self):
        self.run_node(self.MCP_SETUP + '''
register(...known);start();await ready({tools:[{type:"function",function:{name:"mcp__vault_read_note"}},{type:"function",function:{name:"mcp__vault_search_notes"}}]});
fs.writeFileSync(mcpFile,'{"mcpServers":{"vault":{"command":"/bin/sh"}}}');
assert.throws(()=>handlers.get("tool_call")({toolName:"mcp__vault_read_note",input:{},toolCallId:"late-1"},ctx),/MCP connection file changed/);
assert.equal(aborted,true);
''')

    def test_a_provider_request_must_offer_exactly_the_declared_tools(self):
        offered = {
            "an extra tool the model could call": 'tools:[{type:"function",function:{name:"mcp__vault_read_note"}},{type:"function",function:{name:"mcp__vault_search_notes"}},{type:"function",function:{name:"mcp__vault_write_note"}}]',
            "a declared tool missing": 'tools:[{type:"function",function:{name:"mcp__vault_read_note"}}]',
            "no tool list at all": "tools:undefined",
            "a tool list that cannot be read": 'tools:"read_note"',
        }
        for label, payload in offered.items():
            with self.subTest(label):
                self.run_node(self.MCP_SETUP + "register(...known);start();" + '''
await handlers.get("session_start")({},ctx);await handlers.get("before_agent_start")({},ctx);
assert.throws(()=>handlers.get("before_provider_request")({payload:{''' + payload + '''}},ctx),/offered tools outside the declaration/);
assert.equal(aborted,true);
''')

    def test_tools_that_appear_after_session_start_are_removed_before_the_first_turn(self):
        self.run_node(self.MCP_SETUP + '''
register(...known);start();await handlers.get("session_start")({},ctx);
active.push("mcp__vault_write_note");
await handlers.get("before_agent_start")({},ctx);
assert.deepEqual([...active].sort(),["mcp__vault_read_note","mcp__vault_search_notes"]);
''')

    JUDGE_SETUP = '''
const desc=file=>({path:file,sha256:digest(fs.readFileSync(file))});
const questions=path.join(work,"QUESTIONS.json");fs.writeFileSync(questions,'{"schema_version":1,"questions":{}}');
const config=path.join(work,"JUDGE.yml");fs.writeFileSync(config,"modelRoles:\\n  judge: openrouter/typesafe/jev-1.13\\n");
const frozen=path.join(base,"questions.json");fs.copyFileSync(questions,frozen);
const plan=path.join(base,"judge-plan.json");fs.writeFileSync(plan,"{}");
const note=path.join(work,"BG-001.json");fs.writeFileSync(note,'{"id":"BG-001","state":{"note":"x"}}');
const cell='return await (await import("file:///runner.mjs")).run({ judgeBatch, plan: "file:///plan.json" });';
policy.profile="judge";policy.tools=["eval"];policy.write_root=null;
policy.judge={selector:"openrouter/typesafe/jev-1.13",config:desc(config),questions:desc(questions),frozen_questions:desc(frozen),runner:desc(plan),plan:desc(plan),states:{"BG-001":desc(note)},cell_code:cell};
pi.registerTool({name:"eval",execute:async()=>({content:[{type:"text",text:"judged 1/1"}]})});
'''

    def test_only_the_frozen_judge_cell_runs_and_only_once(self):
        self.run_node(self.JUDGE_SETUP + '''
start();await ready();
assert.deepEqual(active,["eval"]);
for(const [label,input] of [["python",{language:"py",code:cell}],["other code",{language:"js",code:"return 1;"}],["extra argument",{language:"js",code:cell,env:{}}]]){
  const blocked=await call("eval",input,label);assert.equal(blocked.block,true,label);
}
const ran=await call("eval",{language:"js",code:cell,title:"Judge runner",timeout:120},"cell-1");assert.equal(ran.content[0].text,"judged 1/1");
const again=await call("eval",{language:"js",code:cell},"cell-2");assert.equal(again.block,true);assert.match(again.reason,/already ran once/);
const rows=fs.readFileSync(policy.guard_log,"utf8").trim().split("\\n").map(line=>JSON.parse(line)).filter(row=>row.type==="decision");
assert.deepEqual(rows.map(row=>[row.call_id,row.allow]),[["python",false],["other code",false],["extra argument",false],["cell-1",true],["cell-2",false]]);
''')

    def test_eval_is_refused_outside_a_judge_run_and_a_changed_judge_input_aborts(self):
        self.run_node('''
pi.registerTool({name:"eval",execute:async()=>({content:[{type:"text",text:"ran"}]})});
start();await ready();
const refused=await call("eval",{language:"js",code:"return 1;"},"eval-1");assert.equal(refused.block,true);assert.match(refused.reason,/not declared/);
''')
        self.run_node(self.JUDGE_SETUP + '''
start();await ready();fs.writeFileSync(questions,'{"schema_version":1,"questions":{"q":{"type":"bool","instructions":"x"}}}');
assert.throws(()=>handlers.get("tool_call")({toolName:"eval",input:{language:"js",code:cell},toolCallId:"late-1"},ctx),/judge input changed/);
assert.equal(aborted,true);
''')


if __name__ == "__main__":
    unittest.main()

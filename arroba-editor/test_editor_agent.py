# SPDX-License-Identifier: AGPL-3.0-or-later
import unittest
from editor_agent import execute_tool, tools_for

class AgentTests(unittest.TestCase):
    def test_rejects_shell(self):
        with self.assertRaises(ValueError):
            execute_tool(None, 'project', 'exec', {'command': 'anything'})

    def test_rejects_other_project(self):
        with self.assertRaises(ValueError):
            execute_tool(None, 'project', 'clip_update', {'path': 'other'})

    def test_scope_injected(self):
        class Client:
            def tool(self, name, **args):
                return args
        result = execute_tool(Client(), 'project', 'clip_transform', {'clipId': 'c1', 'scale': 1.05})
        self.assertEqual(result['path'], 'project')

    def test_tools_are_allowlisted_and_path_hidden(self):
        contract = [{'name': name, 'inputSchema': {'properties': {'path': {'type': 'string'}}, 'required': ['path']}}
                    for name in ['title_add', 'export_start', 'project_open']]
        tools = tools_for(contract)
        self.assertEqual([t['function']['name'] for t in tools], ['title_add'])
        self.assertNotIn('path', tools[0]['function']['parameters']['properties'])

if __name__ == '__main__':
    unittest.main()

import unittest
from ai_context import customer_conversation
from listing_limits import message_page_size
from text_templates import render,contact_variables


class RepoAdaptationTests(unittest.TestCase):
    def test_customer_context_keeps_latest_messages_in_order_with_a_hard_bound(self):
        rows=[{'direction':'in','body':str(i)*1000} for i in range(10)]
        rows.append({'direction':'note','body':'PRIVATE'});rows.append({'direction':'out','body':'PRIVATE','private':True})
        rows.append({'direction':'out','body':'PRIVATE DRAFT','status':'draft'})
        result=customer_conversation(rows)
        self.assertEqual(len(result),8);self.assertTrue(result[-1]['text'].startswith('9'));self.assertNotIn('PRIVATE',str(result));self.assertLessEqual(sum(len(r['text']) for r in result),8000)
    def test_template_variables_are_literal_unknowns_visible_and_growth_is_bounded(self):
        variables=contact_variables({'name':'A','attributes':{'plan':'Starter','city.name':'Bengaluru'}})
        self.assertEqual(render('Hi {{ name }} / {plan} / {{city.name}} / {{missing}}',variables),'Hi A / Starter / Bengaluru / {{missing}}')
        self.assertEqual(render('{{x}}',{'x':'{{name}}'}),'{{name}}')
        with self.assertRaises(ValueError):render('{{x}}'*1000,{'x':'y'*1000})
    def test_untrusted_page_sizes_cannot_load_unbounded_history(self):
        for value in [None,'bad',0,-2,True,float('nan'),float('inf')]:self.assertEqual(message_page_size(value),50)
        self.assertEqual(message_page_size(999999),500);self.assertEqual(message_page_size('2.9'),2)

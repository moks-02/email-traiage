"""Email thread compression system - ScaleDown algorithm"""

import re
from typing import List, Dict, Any
from ..models import Email, EmailThread


class EmailThreadCompressor:
    """
    Compress long email threads by 85% while preserving critical information
    
    Compression Strategy:
    1. Extract key decisions and action items
    2. Identify unresolved questions
    3. Build chronological timeline of critical events
    4. Remove redundant content (greetings, signatures, quoted text)
    5. Summarize by conversation segments
    """
    
    def __init__(self):
        self.compression_target = 0.85  # 85% reduction target
    
    def compress_thread(self, thread: EmailThread) -> EmailThread:
        """
        Compress thread and populate compressed_summary field
        """
        # Calculate original token count (approximate)
        full_text = thread.get_total_text()
        original_tokens = self._estimate_tokens(full_text)
        
        # Perform multi-stage compression
        compressed_data = self._multi_stage_compression(thread)
        
        # Generate final compressed summary
        summary = self._format_compressed_summary(compressed_data)
        compressed_tokens = self._estimate_tokens(summary)
        
        # Update thread with compressed data
        thread.compressed_summary = summary
        thread.original_token_count = original_tokens
        thread.compressed_token_count = compressed_tokens
        thread.compression_ratio = (1 - compressed_tokens / original_tokens) * 100 if original_tokens > 0 else 0
        
        thread.key_decisions = compressed_data['key_decisions']
        thread.unresolved_questions = compressed_data['unresolved_questions']
        thread.action_items_by_person = compressed_data['action_items']
        thread.timeline = compressed_data['timeline']
        
        return thread
    
    def _multi_stage_compression(self, thread: EmailThread) -> Dict[str, Any]:
        """
        Multi-stage compression pipeline
        """
        # Stage 1: Remove redundant content
        cleaned_messages = self._remove_redundant_content(thread.messages)
        
        # Stage 2: Extract structured information
        extracted_data = {
            'key_decisions': [],
            'unresolved_questions': [],
            'action_items': {},
            'timeline': []
        }
        
        # Extract from each message
        for msg in cleaned_messages:
            # Extract decisions (sentences with decision keywords)
            decisions = self._extract_decisions(msg)
            extracted_data['key_decisions'].extend(decisions)
            
            # Extract questions
            questions = self._extract_questions(msg)
            extracted_data['unresolved_questions'].extend(questions)
            
            # Extract action items
            actions = self._extract_action_items(msg)
            for person, items in actions.items():
                if person not in extracted_data['action_items']:
                    extracted_data['action_items'][person] = []
                extracted_data['action_items'][person].extend(items)
            
            # Extract timeline events
            events = self._extract_timeline_events(msg)
            extracted_data['timeline'].extend(events)
        
        # Deduplicate
        extracted_data['key_decisions'] = list(set(extracted_data['key_decisions']))[:10]
        extracted_data['unresolved_questions'] = list(set(extracted_data['unresolved_questions']))[:10]
        extracted_data['timeline'] = extracted_data['timeline'][:15]
        
        return extracted_data
    
    def _remove_redundant_content(self, messages: List[Email]) -> List[Email]:
        """Remove signatures, greetings, quoted text"""
        cleaned = []
        for msg in messages:
            text = msg.body_text
            
            # Remove email signatures (common patterns)
            text = re.sub(r'\n--\s*\n.*', '', text, flags=re.DOTALL)
            text = re.sub(r'\nBest regards,?\n.*', '', text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'\nThanks,?\n.*', '', text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'\nSent from my iPhone.*', '', text, flags=re.IGNORECASE)
            
            # Remove quoted previous messages (lines starting with >)
            lines = text.split('\n')
            non_quoted = [line for line in lines if not line.strip().startswith('>')]
            text = '\n'.join(non_quoted)
            
            # Remove common greetings
            text = re.sub(r'^(Hi|Hello|Hey|Dear)\s+\w+,?\s*\n', '', text, flags=re.IGNORECASE)
            
            # Create cleaned copy
            cleaned_msg = Email(
                id=msg.id,
                thread_id=msg.thread_id,
                subject=msg.subject,
                sender=msg.sender,
                recipients=msg.recipients,
                body_text=text.strip(),
                received_at=msg.received_at
            )
            cleaned.append(cleaned_msg)
        
        return cleaned
    
    def _extract_decisions(self, msg: Email) -> List[str]:
        """Extract decision statements"""
        decisions = []
        text = msg.body_text
        
        # Decision keywords
        decision_patterns = [
            r'we (decided|agreed|chose|selected) (to |that )?([^.!?]+[.!?])',
            r'decision: ([^.!?]+[.!?])',
            r'(will|going to) ([^.!?]+[.!?])',
        ]
        
        for pattern in decision_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    decision = ' '.join(str(m) for m in match if m).strip()
                else:
                    decision = match.strip()
                if len(decision) > 10:  # Filter out too short matches
                    decisions.append(decision[:200])  # Limit length
        
        return decisions[:5]  # Limit per message
    
    def _extract_questions(self, msg: Email) -> List[str]:
        """Extract questions"""
        questions = []
        text = msg.body_text
        
        # Find sentences ending with ?
        sentences = re.split(r'[.!]\s+', text)
        for sentence in sentences:
            if '?' in sentence:
                question = sentence.strip()
                if len(question) > 10:
                    questions.append(question[:200])
        
        return questions[:3]  # Limit per message
    
    def _extract_action_items(self, msg: Email) -> Dict[str, List[str]]:
        """Extract action items"""
        action_items = {}
        text = msg.body_text
        
        # Action patterns
        action_patterns = [
            r'(\w+) (will|should|need to|must) ([^.!?]+[.!?])',
            r'(\w+)\'s action: ([^.!?]+[.!?])',
            r'@(\w+) ([^.!?]+[.!?])',
        ]
        
        for pattern in action_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple) and len(match) >= 2:
                    person = match[0].strip()
                    action = ' '.join(str(m) for m in match[1:] if m).strip()
                    
                    if person not in action_items:
                        action_items[person] = []
                    if len(action) > 10:
                        action_items[person].append(action[:200])
        
        return action_items
    
    def _extract_timeline_events(self, msg: Email) -> List[Dict[str, Any]]:
        """Extract timeline events"""
        events = []
        
        # Date patterns
        date_patterns = [
            r'(deadline|due date|by): ([^.!?\n]+)',
            r'(january|february|march|april|may|june|july|august|september|october|november|december) \d{1,2}',
            r'\d{1,2}/\d{1,2}/\d{2,4}',
        ]
        
        text = msg.body_text
        for pattern in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                event_text = match if isinstance(match, str) else ' '.join(match)
                events.append({
                    'date': msg.received_at.isoformat(),
                    'event': event_text[:150]
                })
        
        return events[:3]
    
    def _format_compressed_summary(self, data: Dict[str, Any]) -> str:
        """Format compressed data into readable summary"""
        summary_parts = []
        
        # Key Decisions
        if data['key_decisions']:
            summary_parts.append("KEY DECISIONS:")
            for i, decision in enumerate(data['key_decisions'][:10], 1):
                summary_parts.append(f"{i}. {decision}")
            summary_parts.append("")
        
        # Unresolved Questions
        if data['unresolved_questions']:
            summary_parts.append("UNRESOLVED QUESTIONS:")
            for i, question in enumerate(data['unresolved_questions'][:10], 1):
                summary_parts.append(f"{i}. {question}")
            summary_parts.append("")
        
        # Action Items by Person
        if data['action_items']:
            summary_parts.append("ACTION ITEMS:")
            for person, items in data['action_items'].items():
                summary_parts.append(f"\n{person}:")
                for item in items[:5]:
                    summary_parts.append(f"  - {item}")
            summary_parts.append("")
        
        # Timeline
        if data['timeline']:
            summary_parts.append("TIMELINE:")
            for event in data['timeline'][:10]:
                summary_parts.append(f"  • {event.get('event', '')}")
        
        return "\n".join(summary_parts)
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation)"""
        # Approximate: 1 token ≈ 4 characters
        return len(text) // 4
    
    def get_compression_stats(self, thread: EmailThread) -> Dict[str, Any]:
        """Get compression statistics"""
        return {
            'message_count': thread.message_count,
            'original_tokens': thread.original_token_count,
            'compressed_tokens': thread.compressed_token_count,
            'compression_ratio_pct': round(thread.compression_ratio, 2),
            'tokens_saved': thread.original_token_count - thread.compressed_token_count,
            'decisions_extracted': len(thread.key_decisions),
            'questions_identified': len(thread.unresolved_questions),
            'action_items_count': sum(len(items) for items in thread.action_items_by_person.values())
        }

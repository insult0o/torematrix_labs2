"""
Email Handler for Agent 4 - Email format processing (MSG, EML).
"""

import asyncio
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List, Any, Optional, Dict, Tuple
from email import message_from_string
from email.header import decode_header

logger = logging.getLogger(__name__)


@dataclass
class EmailFeatures:
    """Features detected in email documents."""
    format_type: str = "eml"  # eml, msg
    has_attachments: bool = False
    has_html_body: bool = False
    has_text_body: bool = False
    has_inline_images: bool = False
    is_multipart: bool = False
    sender: Optional[str] = None
    recipients: List[str] = None
    subject: Optional[str] = None
    date: Optional[str] = None
    message_id: Optional[str] = None
    attachment_count: int = 0
    body_size: int = 0
    
    def __post_init__(self):
        if self.recipients is None:
            self.recipients = []


class EmailHandler:
    """Email document handler for MSG and EML formats."""
    
    def __init__(self, client=None):
        self.client = client
        
    async def process(self, file_path: Path, **kwargs) -> Tuple[List[Any], EmailFeatures]:
        """Process email documents with format-specific handling."""
        try:
            # Analyze email features
            content, features = await self._analyze_email_document(file_path)
            
            # Process based on email format
            if features.format_type == "msg":
                elements = await self._process_msg_email(file_path, content, features, **kwargs)
            else:  # EML
                elements = await self._process_eml_email(content, features, **kwargs)
            
            logger.info(f"Email processed: {features.format_type}, {len(elements)} elements")
            return elements, features
            
        except Exception as e:
            logger.error(f"Email processing failed for {file_path}: {e}")
            return [self._create_fallback_element(file_path, str(e))], EmailFeatures()
    
    async def _analyze_email_document(self, file_path: Path) -> Tuple[str, EmailFeatures]:
        """Analyze email document to detect features."""
        features = EmailFeatures()
        
        try:
            suffix = file_path.suffix.lower()
            
            if suffix == '.msg':
                features.format_type = "msg"
                content, features = await self._analyze_msg_features(file_path, features)
            else:  # .eml or other
                features.format_type = "eml"
                content, features = await self._analyze_eml_features(file_path, features)
            
            return content, features
            
        except Exception as e:
            logger.warning(f"Email analysis failed: {e}")
            return "", EmailFeatures()
    
    async def _analyze_eml_features(self, file_path: Path, features: EmailFeatures) -> Tuple[str, EmailFeatures]:
        """Analyze EML email features."""
        try:
            # Read EML file
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            
            # Parse email message
            msg = message_from_string(content)
            
            # Extract headers
            features.sender = self._decode_header(msg.get('From', ''))
            features.subject = self._decode_header(msg.get('Subject', ''))
            features.date = msg.get('Date', '')
            features.message_id = msg.get('Message-ID', '')
            
            # Extract recipients
            to_header = msg.get('To', '')
            cc_header = msg.get('Cc', '')
            bcc_header = msg.get('Bcc', '')
            
            for header in [to_header, cc_header, bcc_header]:
                if header:
                    recipients = [r.strip() for r in header.split(',')]
                    features.recipients.extend(recipients)
            
            # Analyze message structure
            features.is_multipart = msg.is_multipart()
            
            if features.is_multipart:
                for part in msg.walk():
                    content_type = part.get_content_type()
                    
                    if content_type == 'text/plain':
                        features.has_text_body = True
                        body = part.get_payload(decode=True)
                        if body:
                            features.body_size += len(body)
                    elif content_type == 'text/html':
                        features.has_html_body = True
                        body = part.get_payload(decode=True)
                        if body:
                            features.body_size += len(body)
                    elif part.get_filename():
                        features.has_attachments = True
                        features.attachment_count += 1
                    elif 'image' in content_type and part.get('Content-ID'):
                        features.has_inline_images = True
            else:
                # Single part message
                content_type = msg.get_content_type()
                if content_type == 'text/html':
                    features.has_html_body = True
                else:
                    features.has_text_body = True
                
                body = msg.get_payload(decode=True)
                if body:
                    features.body_size = len(body)
            
            return content, features
            
        except Exception as e:
            logger.warning(f"EML analysis failed: {e}")
            return "", features
    
    async def _analyze_msg_features(self, file_path: Path, features: EmailFeatures) -> Tuple[str, EmailFeatures]:
        """Analyze MSG email features."""
        try:
            # MSG files require special handling (would use extract-msg in production)
            # For now, simulate analysis based on file properties
            file_size = file_path.stat().st_size
            
            features.sender = "sender@example.com"  # Would extract from MSG
            features.subject = f"Email from {file_path.stem}"
            features.has_attachments = file_size > 100 * 1024  # Assume large files have attachments
            features.has_html_body = True  # Most modern emails have HTML
            features.has_text_body = True
            features.is_multipart = True
            features.body_size = max(1000, file_size // 10)
            
            # Read as binary and convert to string representation
            with open(file_path, 'rb') as f:
                raw_content = f.read()
                # Create a string representation
                content = f"MSG Email File: {file_path.name}\nSize: {len(raw_content)} bytes"
            
            return content, features
            
        except Exception as e:
            logger.warning(f"MSG analysis failed: {e}")
            return "", features
    
    def _decode_header(self, header_value: str) -> str:
        """Decode email header value."""
        try:
            decoded_parts = decode_header(header_value)
            decoded_string = ""
            
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    if encoding:
                        decoded_string += part.decode(encoding)
                    else:
                        decoded_string += part.decode('utf-8', errors='replace')
                else:
                    decoded_string += part
            
            return decoded_string.strip()
            
        except Exception as e:
            logger.warning(f"Header decoding failed: {e}")
            return header_value
    
    async def _process_eml_email(self, content: str, features: EmailFeatures, **kwargs) -> List[Any]:
        """Process EML email format."""
        if self.client:
            # Use client if available - create temp file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.eml', delete=False, encoding='utf-8') as f:
                f.write(content)
                temp_path = Path(f.name)
            
            try:
                return await self.client.parse_document(temp_path, **kwargs)
            finally:
                temp_path.unlink()
        else:
            # Fallback EML processing
            elements = []
            
            # Email metadata
            if features.subject:
                elements.append(self._create_element("EmailSubject", features.subject))
            
            if features.sender:
                elements.append(self._create_element("EmailSender", features.sender))
            
            for recipient in features.recipients[:5]:  # Limit for demo
                if recipient.strip():
                    elements.append(self._create_element("EmailRecipient", recipient.strip()))
            
            if features.date:
                elements.append(self._create_element("EmailDate", features.date))
            
            # Email body content
            try:
                msg = message_from_string(content)
                body_text = self._extract_email_body(msg, features)
                
                if body_text:
                    # Split into paragraphs
                    paragraphs = body_text.split('\n\n')
                    for paragraph in paragraphs[:5]:  # Limit for demo
                        paragraph = paragraph.strip()
                        if len(paragraph) > 20:
                            elements.append(self._create_element("EmailBody", paragraph))
                            
            except Exception as e:
                logger.warning(f"Email body extraction failed: {e}")
                elements.append(self._create_element("EmailBody", "Email body content"))
            
            # Attachments
            if features.has_attachments:
                for i in range(features.attachment_count):
                    elements.append(self._create_element("EmailAttachment", f"Attachment {i+1}"))
            
            return elements
    
    async def _process_msg_email(self, file_path: Path, content: str, features: EmailFeatures, **kwargs) -> List[Any]:
        """Process MSG email format."""
        if self.client:
            return await self.client.parse_document(file_path, **kwargs)
        else:
            # Fallback MSG processing
            elements = [
                self._create_element("EmailSubject", features.subject or f"MSG Email: {file_path.stem}"),
                self._create_element("EmailSender", features.sender or "Unknown Sender"),
                self._create_element("EmailBody", f"MSG email content from {file_path.name}"),
                self._create_element("NarrativeText", f"Email size: {features.body_size} bytes")
            ]
            
            if features.has_attachments:
                elements.append(self._create_element("EmailAttachment", "MSG attachments detected"))
            
            return elements
    
    def _extract_email_body(self, msg, features: EmailFeatures) -> str:
        """Extract text body from email message."""
        body_text = ""
        
        if features.is_multipart:
            for part in msg.walk():
                content_type = part.get_content_type()
                
                if content_type == 'text/plain':
                    payload = part.get_payload(decode=True)
                    if payload:
                        try:
                            body_text += payload.decode('utf-8', errors='replace') + "\n"
                        except Exception:
                            body_text += str(payload) + "\n"
                elif content_type == 'text/html' and not body_text:
                    # Use HTML if no plain text available
                    payload = part.get_payload(decode=True)
                    if payload:
                        try:
                            html_content = payload.decode('utf-8', errors='replace')
                            # Simple HTML to text conversion
                            body_text = self._html_to_text(html_content)
                        except Exception:
                            body_text = str(payload)
        else:
            # Single part message
            payload = msg.get_payload(decode=True)
            if payload:
                try:
                    content = payload.decode('utf-8', errors='replace')
                    if msg.get_content_type() == 'text/html':
                        body_text = self._html_to_text(content)
                    else:
                        body_text = content
                except Exception:
                    body_text = str(payload)
        
        return body_text.strip()
    
    def _html_to_text(self, html_content: str) -> str:
        """Convert HTML to plain text (simplified)."""
        try:
            # Remove scripts and styles
            html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.IGNORECASE | re.DOTALL)
            html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.IGNORECASE | re.DOTALL)
            
            # Convert common HTML elements
            html_content = re.sub(r'<br[^>]*>', '\n', html_content, flags=re.IGNORECASE)
            html_content = re.sub(r'<p[^>]*>', '\n', html_content, flags=re.IGNORECASE)
            html_content = re.sub(r'</p>', '\n', html_content, flags=re.IGNORECASE)
            
            # Remove all HTML tags
            text = re.sub(r'<[^>]+>', '', html_content)
            
            # Clean up whitespace
            text = re.sub(r'\n\s*\n', '\n\n', text)
            text = re.sub(r'[ \t]+', ' ', text)
            
            return text.strip()
            
        except Exception as e:
            logger.warning(f"HTML to text conversion failed: {e}")
            return html_content
    
    def _create_element(self, element_type: str, text: str) -> Any:
        """Create a mock element for fallback processing."""
        from unittest.mock import Mock
        element = Mock()
        element.category = element_type
        element.text = text
        element.metadata = {"agent": "Agent 4 Email Handler"}
        return element
    
    def _create_fallback_element(self, file_path: Path, error: str) -> Any:
        """Create fallback element when processing fails."""
        return self._create_element("Error", f"Email processing failed for {file_path.name}: {error}")
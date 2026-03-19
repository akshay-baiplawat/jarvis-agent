import datetime
import logging
from dotenv import load_dotenv
from livekit.agents import function_tool, RunContext
import requests
import os
import smtplib
from email.mime.multipart import MIMEMultipart  
from email.mime.text import MIMEText
from typing import Optional
import pytz
from mem0 import MemoryClient

load_dotenv(".env")

# Initialize Mem0 client
mem0_client = MemoryClient(api_key=os.getenv("MEM0_API_KEY"))

@function_tool()
async def get_weather(
    context: RunContext,  # type: ignore
    city: str) -> str:
    """
    Get the current weather information for a specified city.
    
    Args:
        city: Name of the city to get weather for
    """
    try:
        # Input validation
        if not city or not city.strip():
            return "Weather request failed: City name cannot be empty."
        
        city = city.strip()
        
        # Use format=3 for current weather only (concise format)
        # Alternative formats: format=1 (one line), format=2 (two lines), format=4 (detailed)
        response = requests.get(
            f"https://wttr.in/{city}?format=3",
            timeout=10,  # Add timeout to prevent hanging
            headers={'User-Agent': 'Jarvis-Weather-Tool/1.0'}  # Identify the request
        )
        
        if response.status_code == 200:
            weather_info = response.text.strip()
            
            # Check if the response indicates city not found
            if "not found" in weather_info.lower() or len(weather_info) < 10:
                logging.warning(f"City '{city}' not found in weather service")
                return f"Weather data unavailable: City '{city}' not found."
            
            # Format the response in Jarvis style
            logging.info(f"Weather retrieved for {city}: {weather_info}")
            return f"Affirmative; current weather for {city} is {weather_info}."
            
        elif response.status_code == 404:
            return f"Weather data unavailable: City '{city}' not found in the weather database."
        elif response.status_code == 429:
            return "Weather service temporarily unavailable: Rate limit exceeded, please try again later."
        else:
            logging.error(f"Weather API returned status {response.status_code} for {city}")
            return f"Weather service error: Unable to retrieve data (status: {response.status_code})."
            
    except requests.exceptions.Timeout:
        logging.error(f"Timeout error when fetching weather for {city}")
        return "Weather request failed: Service timeout, please try again."
    
    except requests.exceptions.ConnectionError:
        logging.error(f"Connection error when fetching weather for {city}")
        return "Weather request failed: Unable to connect to weather service."
    
    except requests.exceptions.RequestException as e:
        logging.error(f"Request error fetching weather for {city}: {e}")
        return "Weather request failed: Network error occurred."
    
    except Exception as e:
        logging.error(f"Unexpected error fetching weather for {city}: {e}")
        return f"An unexpected error occurred while retrieving weather data: {str(e)}"

@function_tool()
async def search_web(
    context: RunContext,  # type: ignore
    query: str) -> str:
    """
    Search the web using Perplexity AI for current and comprehensive information.
    """
    try:
        # Get Perplexity API key from environment variables
        api_key = os.getenv("PERPLEXITY_API_KEY")
        
        if not api_key:
            logging.error("Perplexity API key not found in environment variables")
            return "Web search failed: Perplexity API key not configured."

        # Perplexity API endpoint
        url = "https://api.perplexity.ai/chat/completions"
        
        # Headers
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Request payload
        payload = {
            "model": "sonar-pro",  # Use the flagship model for best results
            "messages": [
                {
                    "role": "system",
                    "content": "You are a helpful assistant that provides accurate, concise, and current information. Include relevant sources and citations when possible."
                },
                {
                    "role": "user", 
                    "content": query
                }
            ],
            "max_tokens": 1000,
            "temperature": 0.2,  # Lower temperature for more focused results
            "top_p": 0.9,
            "return_images": False,
            "return_related_questions": False,
            "search_domain_filter": [],  # No domain restrictions
            "search_recency_filter": "month"  # Focus on recent content
        }
        
        # Make the API request
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            
            # Extract the main response
            answer = result["choices"][0]["message"]["content"]
            
            # Optionally include source information if available
            sources = []
            if "search_results" in result:
                for source in result["search_results"][:3]:  # Limit to top 3 sources
                    sources.append(f"- {source.get('title', 'Unknown')}: {source.get('url', '')}")
            
            # Combine answer with sources if available
            if sources:
                full_response = f"{answer}\n\nSources:\n" + "\n".join(sources)
            else:
                full_response = answer
                
            logging.info(f"Web search successful for query: '{query}'")
            return full_response
            
        else:
            logging.error(f"Perplexity API error: {response.status_code} - {response.text}")
            return f"Web search failed: API returned status code {response.status_code}"
            
    except requests.exceptions.Timeout:
        logging.error(f"Timeout error when searching for: '{query}'")
        return "Web search failed: Request timed out."
    except requests.exceptions.RequestException as e:
        logging.error(f"Network error searching for '{query}': {e}")
        return f"Web search failed: Network error occurred."
    except Exception as e:
        logging.error(f"Unexpected error searching for '{query}': {e}")
        return f"An unexpected error occurred while searching: {str(e)}"
    
@function_tool()
async def send_email(
    context: RunContext,  # type: ignore
    to_email: str,
    subject: str,
    message: str,
    cc_email: Optional[str] = None
) -> str:
    """
    Send an email through Gmail with proper authentication and error handling.
    
    Args:
        to_email: Recipient email address (required)
        subject: Email subject line (required)
        message: Email body content (required)
        cc_email: Optional CC email address
    """
    import re
    
    def validate_email(email: str) -> bool:
        """Validate email format"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    try:
        # Input validation
        if not to_email or not validate_email(to_email):
            return "Email sending failed: Invalid recipient email address."
        
        if cc_email and not validate_email(cc_email):
            return "Email sending failed: Invalid CC email address."
            
        if not subject.strip():
            return "Email sending failed: Subject line cannot be empty."
            
        if not message.strip():
            return "Email sending failed: Message body cannot be empty."
        
        # Gmail SMTP configuration
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        
        # Get credentials from environment variables
        gmail_user = os.getenv("GMAIL_USER")
        gmail_password = os.getenv("GMAIL_APP_PASSWORD")  # Use App Password
        
        if not gmail_user or not gmail_password:
            logging.error("Gmail credentials not found in environment variables")
            return "Affirmative; however, email sending failed as Gmail credentials are not configured."
        
        # Validate sender email
        if not validate_email(gmail_user):
            return "Email sending failed: Invalid sender email configuration."
        
        # Create message with improved formatting
        msg = MIMEMultipart('alternative')
        msg['From'] = f"Jarvis Assistant <{gmail_user}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Add CC if provided
        recipients = [to_email]
        if cc_email:
            msg['Cc'] = cc_email
            recipients.append(cc_email)
        
        # Create both plain text and HTML versions
        text_part = MIMEText(message, 'plain')
        
        # Optional: Create HTML version with better formatting
        html_message = f"""
        <html>
          <body>
            <p style="font-family: Arial, sans-serif; font-size: 14px;">
              {message.replace('\n', '<br>')}
            </p>
            <hr style="border: 1px solid #ccc; margin-top: 20px;">
            <p style="font-family: Arial, sans-serif; font-size: 12px; color: #666;">
              <em>This email was sent by Jarvis AI Assistant</em>
            </p>
          </body>
        </html>
        """
        html_part = MIMEText(html_message, 'html')
        
        # Attach both versions
        msg.attach(text_part)
        msg.attach(html_part)
        
        # Connect to Gmail SMTP server with improved error handling
        server = None
        try:
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.set_debuglevel(0)  # Set to 1 for debugging
            server.starttls()  # Enable TLS encryption
            
            # Login with better error handling
            server.login(gmail_user, gmail_password)
            
            # Send email
            server.sendmail(gmail_user, recipients, msg.as_string())
            
            # Prepare success message
            cc_info = f" with CC to {cc_email}" if cc_email else ""
            logging.info(f"Email sent successfully to {to_email}{cc_info}")
            
            return f"Understood; email with subject '{subject}' has been sent successfully to {to_email}{cc_info}."
            
        finally:
            if server:
                try:
                    server.quit()
                except:
                    pass  # Ignore errors when closing connection
        
    except smtplib.SMTPAuthenticationError as e:
        logging.error(f"Gmail authentication failed: {e}")
        return "Email sending failed: Authentication error - please verify your Gmail App Password is correct."
    
    except smtplib.SMTPRecipientsRefused as e:
        logging.error(f"Recipients refused: {e}")
        return f"Email sending failed: One or more recipient addresses were refused by the server."
    
    except smtplib.SMTPSenderRefused as e:
        logging.error(f"Sender refused: {e}")
        return "Email sending failed: Sender address was refused by the server."
    
    except smtplib.SMTPDataError as e:
        logging.error(f"SMTP data error: {e}")
        return "Email sending failed: Server rejected the email data."
    
    except smtplib.SMTPException as e:
        logging.error(f"SMTP error occurred: {e}")
        return f"Email sending failed: SMTP error - {str(e)}"
    
    except ConnectionError as e:
        logging.error(f"Connection error: {e}")
        return "Email sending failed: Could not connect to Gmail servers. Please check your internet connection."
    
    except Exception as e:
        logging.error(f"Unexpected error sending email: {e}")
        return f"An unexpected error occurred while sending email: {str(e)}"

@function_tool()
async def save_memory(
    context: RunContext,  # type: ignore
    memory_content: str,
    category: str = "general"
) -> str:
    """
    When the user says "remember that…" or "I prefer…", or similar, call the save_memory tool to store that preference.

    Args:
        memory_content: The information to remember
        category: Category for organizing memories (preferences, tasks, meetings, etc.)
    """
    try:
        # Input validation
        if not memory_content or not memory_content.strip():
            return "Memory storage failed: Cannot save empty content."
        
        # Get user ID from environment
        user_id = os.environ.get("USER_ID", "default_user")
        
        if not user_id or user_id == "default_user":
            logging.warning("Using default user ID - consider setting USER_ID environment variable")
        
        # Validate API key
        api_key = os.getenv("MEM0_API_KEY")
        if not api_key:
            logging.error("MEM0_API_KEY not found in environment variables")
            return "Memory storage failed: Mem0 API key not configured."
        
        # Clean and prepare memory content
        memory_content = memory_content.strip()
        
        # Create messages in the correct format for Mem0 API
        messages = [
            {
                "role": "user",
                "content": memory_content
            }
        ]
        
        # Prepare metadata with additional context
        metadata = {
            "category": category,
            "timestamp": datetime.datetime.now().isoformat(),
            "source": "jarvis_assistant"
        }
        
        # Call Mem0 API with correct parameters
        result = mem0_client.add(
            messages=messages,
            user_id=user_id,
            metadata=metadata,
            output_format="v1.1"  # Use enhanced output format
        )
        
        # Log successful storage
        logging.info(f"Memory stored successfully for user {user_id}: {memory_content[:50]}...")
        
        # Check if result contains the created memory information
        if hasattr(result, 'memories') and result.memories:
            memory_id = result.memories[0].get('id', 'unknown')
            return f"Affirmative; I've stored this memory in category '{category}': {memory_content}"
        else:
            return f"Affirmative; I've stored this memory: {memory_content}"
            
    except Exception as e:
        error_message = str(e).lower()
        
        # Handle specific error types
        if "400" in error_message or "bad request" in error_message:
            if "required" in error_message:
                logging.error(f"Missing required identifier in Mem0 request: {e}")
                return "Memory storage failed: Missing required user identifier."
            else:
                logging.error(f"Bad request to Mem0 API: {e}")
                return "Memory storage failed: Invalid request format."
        
        elif "401" in error_message or "unauthorized" in error_message:
            logging.error(f"Mem0 API authentication failed: {e}")
            return "Memory storage failed: Invalid API credentials."
        
        elif "403" in error_message or "forbidden" in error_message:
            logging.error(f"Mem0 API access forbidden: {e}")
            return "Memory storage failed: Access denied - check API permissions."
        
        elif "429" in error_message or "rate limit" in error_message:
            logging.error(f"Mem0 API rate limit exceeded: {e}")
            return "Memory storage failed: Rate limit exceeded, please try again later."
        
        elif "timeout" in error_message:
            logging.error(f"Timeout error with Mem0 API: {e}")
            return "Memory storage failed: Request timed out, please try again."
        
        else:
            logging.error(f"Unexpected error saving memory: {e}")
            return f"Memory storage failed: {str(e)}"


@function_tool()
async def save_memory_simple(
    context: RunContext,  # type: ignore
    memory_content: str,
    category: str = "general"
) -> str:
    """
    Alternative implementation using the simpler text parameter format.
    Use this if the messages format above doesn't work.
    
    Args:
        memory_content: The information to remember
        category: Category for organizing memories
    """
    try:
        # Input validation
        if not memory_content or not memory_content.strip():
            return "Memory storage failed: Cannot save empty content."
        
        user_id = os.environ.get("USER_ID", "default_user")
        memory_content = memory_content.strip()
        
        # Prepare metadata
        metadata = {
            "category": category,
            "timestamp": datetime.datetime.now().isoformat(),
            "source": "jarvis_assistant"
        }
        
        # Use the simpler text format instead of messages
        result = mem0_client.add(
            text=memory_content,
            user_id=user_id,
            metadata=metadata,
            output_format="v1.1"
        )
        
        logging.info(f"Memory stored successfully using text format: {memory_content[:50]}...")
        return f"Affirmative; I've stored this memory in category '{category}': {memory_content}"
        
    except Exception as e:
        logging.error(f"Error saving memory with text format: {e}")
        return f"Memory storage failed: {str(e)}"


@function_tool()
async def save_memory_with_context(
    context: RunContext,  # type: ignore
    memory_content: str,
    category: str = "general",
    additional_context: str = None
) -> str:
    """
    Enhanced version that can save memory with additional context from the conversation.
    
    Args:
        memory_content: The main information to remember
        category: Category for organizing memories
        additional_context: Optional additional context or conversation history
    """
    try:
        if not memory_content or not memory_content.strip():
            return "Memory storage failed: Cannot save empty content."
        
        user_id = os.environ.get("USER_ID", "default_user")
        
        # Create enhanced messages with context if provided
        messages = [
            {
                "role": "user",
                "content": memory_content
            }
        ]
        
        # Add context as a system message if provided
        if additional_context and additional_context.strip():
            messages.insert(0, {
                "role": "assistant",
                "content": f"Context: {additional_context.strip()}"
            })
        
        # Enhanced metadata with more details
        metadata = {
            "category": category,
            "timestamp": datetime.datetime.now().isoformat(),
            "source": "jarvis_assistant",
            "has_context": bool(additional_context),
            "content_length": len(memory_content)
        }
        
        result = mem0_client.add(
            messages=messages,
            user_id=user_id,
            metadata=metadata,
            output_format="v1.1"
        )
        
        context_note = " with context" if additional_context else ""
        logging.info(f"Enhanced memory stored{context_note}: {memory_content[:50]}...")
        
        return f"Affirmative; I've stored this memory in category '{category}'{context_note}: {memory_content}"
        
    except Exception as e:
        logging.error(f"Error saving enhanced memory: {e}")
        return f"Memory storage failed: {str(e)}"

@function_tool()
async def search_memories(
    context: RunContext,  # type: ignore
    query: str,
    limit: int = 5
) -> str:
    """
    Search through stored memories for relevant information.
    
    Args:
        query: What to search for in memories
        limit: Maximum number of memories to return
    """
    try:
        user_id = os.environ.get("USER_ID", "default_user")
        
        results = mem0_client.search(
            query,
            user_id=user_id,
            limit=limit
        )
        
        if not results:
            return "I don't have any relevant memories about that topic."
            
        memories = []
        for result in results:
            memories.append(f"• {result['memory']}")
            
        return f"Here's what I remember:\n" + "\n".join(memories)
        
    except Exception as e:
        logging.error(f"Error searching memories: {e}")
        return f"Memory search failed: {str(e)}"

@function_tool()
async def get_all_memories(
    context: RunContext,  # type: ignore
    category: str = None
) -> str:
    """
    Get all stored memories, optionally filtered by category.
    
    Args:
        category: Optional category to filter by
    """
    try:
        user_id = os.environ.get("USER_ID", "default_user")
        
        memories = mem0_client.get_all(user_id=user_id)
        
        if category:
            memories = [m for m in memories if m.get('metadata', {}).get('category') == category]
            
        if not memories:
            return f"No memories found{f' in category {category}' if category else ''}."
            
        memory_list = []
        for memory in memories[:10]:  # Limit to 10 most recent
            cat = memory.get('metadata', {}).get('category', 'general')
            memory_list.append(f"[{cat}] {memory['memory']}")
            
        return f"Your stored memories:\n" + "\n".join(memory_list)
        
    except Exception as e:
        logging.error(f"Error retrieving memories: {e}")
        return f"Memory retrieval failed: {str(e)}"

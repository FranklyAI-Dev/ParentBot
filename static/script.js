// Wait for the entire HTML document to be loaded
document.addEventListener('DOMContentLoaded', () => {
    
    // --- 1. GET ALL HTML ELEMENTS ---
    const chatWindow = document.getElementById('chat-window');
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');

    // --- 2. STATE MANAGEMENT ---
    // We only need to store the history for the *current session*
    let chatHistory = [];
    
    console.log("ParentBot Chat UI is ready.");

    // --- 3. CORE FUNCTIONS ---

    /**
     * Sends a new chat message to the server.
     */
    async function handleSendMessage() {
        const message = messageInput.value.trim();
        if (message === "") return;

        // Add user message to UI
        addMessage(message, 'user-message');
        // Add user message to history
        chatHistory.push({ role: 'user', text: message });
        
        messageInput.value = ""; // Clear the input
        updateChatUI(false); // Disable input while AI is thinking
        addMessage("Turmeric is thinking...", 'ai-message', true); // Add temporary thinking message

        try {
            // Use relative URL /chat
            const response = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    // Send the new message AND the entire history
                    message: message,
                    history: chatHistory 
                })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || "Error from server");
            }

            const data = await response.json();
            
            // Remove the "Thinking..." message
            const thinkingMessage = document.getElementById('thinking-message');
            if (thinkingMessage) {
                thinkingMessage.remove();
            }
            
            // Add the real AI reply
            addMessage(data.reply, 'ai-message');
            // Add AI reply to history
            chatHistory.push({ role: 'model', text: data.reply });
            
        } catch (error) {
            console.error("Chat error:", error);
            const thinkingMessage = document.getElementById('thinking-message');
            if (thinkingMessage) {
                thinkingMessage.remove();
            }
            addErrorMessage(`Error: ${error.message}`);
        } finally {
            updateChatUI(true); // Re-enable chat UI
        }
    }

    // --- 4. HELPER & UI FUNCTIONS ---

    function addMessage(text, className, isThinking = false) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('message', className);
        messageElement.textContent = text;
        
        if (isThinking) {
            messageElement.id = 'thinking-message';
        }
        
// --- THIS IS THE UPGRADE ---
        // If it's an AI message, parse the Markdown and sanitize the HTML
        // Otherwise, just use safe textContent (for user messages)
        if (className === 'ai-message' && !isThinking) {
            // 1. Convert Markdown text to raw HTML
            const rawHtml = marked.parse(text);
            // 2. Sanitize the HTML to prevent security risks
            const cleanHtml = DOMPurify.sanitize(rawHtml);
            // 3. Render the clean, formatted HTML
            messageElement.innerHTML = cleanHtml;
        } else {
            // Use .textContent for user messages and "thinking" messages
            // This is safer as it prevents rendering any text as HTML
            messageElement.textContent = text;
        }
// --- END OF UPGRADE ---

        chatWindow.appendChild(messageElement);
        chatWindow.scrollTop = chatWindow.scrollHeight; // Auto-scroll to bottom
    }
    
    function addErrorMessage(text) {
        addMessage(text, 'system-message');
    }

    function updateChatUI(enabled) {
        messageInput.disabled = !enabled;
        sendButton.disabled = !enabled;
        if (!enabled) {
            messageInput.placeholder = "Please wait...";
        } else {
            messageInput.placeholder = "Type your question...";
        }
    }
    
    // --- 5. ATTACH EVENT LISTENERS ---
    
    // When the send button is clicked
    sendButton.addEventListener('click', handleSendMessage);
    
    // When Enter is pressed in the message input
    messageInput.addEventListener('keypress', (event) => {
        if (event.key === 'Enter' && !sendButton.disabled) {
            handleSendMessage();
        }
    });

    // --- 6. INITIALIZE THE APP ---
    // No initialization needed, just wait for user input.
    updateChatUI(true);
});
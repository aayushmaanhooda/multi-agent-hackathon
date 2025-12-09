const API_URL = "http://localhost:8000";

export const api = {
    login: async (email, password) => {
        const response = await fetch(`${API_URL}/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password }),
            credentials: "include" // Important for cookies
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "Login failed");
        }
        return await response.json();
    },

    register: async (userData) => {
        // userData contains: name, email, password, role, access_code (if admin)
        const response = await fetch(`${API_URL}/register`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(userData),
            credentials: "include"
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "Registration failed");
        }
        return await response.json();
    }, // Added missing comma here
    getMe: async () => {
        const response = await fetch(`${API_URL}/dashboard`, {
            headers: { "Content-Type": "application/json" },
            credentials: "include"
        });
        if (!response.ok) throw new Error("Not authenticated");
        return await response.json();
    },

    logout: async () => {
        await fetch(`${API_URL}/logout`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "include"
        });
    },

    chat: async (message, conversationId = null) => {
        const response = await fetch(`${API_URL}/chat`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            credentials: "include",
            body: JSON.stringify({
                message: message,
                conversation_id: conversationId
            })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "Chat request failed");
        }
        return await response.json();
    }
};

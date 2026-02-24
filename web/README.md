# AI Study System - Web Interface

A modern web interface for the AI-assisted study system, built with FastAPI backend and vanilla HTML/CSS/JavaScript frontend.

## Features

- 📊 **Dashboard**: Overview of study materials, topics, and progress
- 📚 **Materials Management**: Add, view, and organize study materials
- 🏷️ **Topic Organization**: Create and manage study topics
- 🔍 **Smart Search**: Semantic and text-based search through materials
- 🤖 **AI Content Generation**: Generate study content with AI assistance
- 📱 **Responsive Design**: Works on desktop and mobile devices

## Quick Start

### Prerequisites

- Python 3.8+
- StudySystem backend (from Parts 1-3)

### Installation

1. **Install dependencies:**
   ```bash
   cd web
   pip install -r requirements.txt
   ```

2. **Start the web server:**
   ```bash
   python api.py
   ```

3. **Open your browser:**
   ```
   http://localhost:8000
   ```

The web interface will automatically connect to the StudySystem backend.

## API Endpoints

The FastAPI backend provides the following endpoints:

### Materials
- `GET /api/materials` - List all materials
- `POST /api/materials` - Add new material
- `GET /api/materials/{id}` - Get specific material
- `PUT /api/materials/{id}` - Update material
- `DELETE /api/materials/{id}` - Delete material

### Search
- `POST /api/search` - Semantic search
- `GET /api/search/text` - Text-based search

### Topics
- `GET /api/topics` - List all topics
- `POST /api/topics` - Create new topic
- `GET /api/topics/{id}` - Get specific topic
- `PUT /api/topics/{id}` - Update topic
- `DELETE /api/topics/{id}` - Delete topic

### Content Generation
- `POST /api/generate` - Generate study content

### Statistics
- `GET /api/stats` - Get system statistics

## Frontend Architecture

### Files
- `frontend/index.html` - Main HTML structure
- `frontend/styles.css` - Modern responsive styling
- `frontend/app.js` - Interactive functionality

### Key Components
- **Tabbed Navigation**: Dashboard, Materials, Topics, Search, Generate
- **Modal Forms**: For adding materials and topics
- **Responsive Grid**: Adapts to different screen sizes
- **Real-time Updates**: Dynamic content loading via API

## Development

### Adding New Features

1. **Backend**: Add new endpoints to `api.py`
2. **Frontend**: Update HTML structure in `index.html`
3. **Styling**: Add CSS rules in `styles.css`
4. **JavaScript**: Implement functionality in `app.js`

### API Integration

The frontend uses the `StudySystemApp` class to handle all API interactions:

```javascript
// Example: Load materials
async loadMaterials() {
    const response = await fetch('/api/materials');
    const data = await response.json();
    // Update UI with data
}
```

## Browser Support

- Chrome 90+
- Firefox 88+
- Safari 14+
- Edge 90+

## Troubleshooting

### Common Issues

1. **"Failed to load dashboard data"**
   - Check that the StudySystem backend is running
   - Verify API endpoints are accessible

2. **Content generation not working**
   - Ensure OpenAI API key is configured in StudySystem
   - Check browser console for error details

3. **Styling issues**
   - Clear browser cache
   - Check that all CSS files are loading

### Development Tips

- Use browser developer tools to inspect API calls
- Check the browser console for JavaScript errors
- Test on multiple screen sizes for responsiveness

## Contributing

1. Follow the existing code style
2. Add comments for complex logic
3. Test on multiple browsers
4. Update this README for new features

## License

This project is part of the AI Study System implementation.
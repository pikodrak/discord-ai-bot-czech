# Frontend Admin Interface

This directory contains the frontend admin interface for the Discord AI Bot.

## Overview

The admin interface is a single-page application built with vanilla JavaScript, HTML, and CSS. It provides a clean, modern interface for managing the Discord bot configuration and monitoring its status.

## Features

### Authentication
- **Login Page**: Secure JWT-based authentication
- **Session Management**: Automatic token storage and session persistence
- **Auto-logout**: Redirects to login on token expiration

### Bot Management
- **Status Monitoring**: Real-time bot status with visual indicators
- **Control Panel**: Start, stop, and restart bot with one click
- **Statistics Dashboard**: View message counts, response times, and uptime
- **Auto-refresh**: Status updates every 10 seconds

### Configuration Management
- **View Current Settings**: Display all bot configuration parameters
- **Update Configuration**: Modify bot behavior settings
- **Reload from File**: Reload configuration from .env file
- **Validate Configuration**: Check configuration validity

### System Health
- **Health Dashboard**: Monitor API and service health
- **Provider Status**: Check Discord and AI API configuration
- **Version Information**: Display API version details

## File Structure

```
static/
├── index.html          # Main HTML page
├── css/
│   └── style.css       # Stylesheet with modern design
├── js/
│   └── app.js          # JavaScript application logic
└── README.md           # This file
```

## Technology Stack

- **HTML5**: Semantic markup
- **CSS3**: Modern styling with CSS variables and flexbox/grid
- **Vanilla JavaScript**: No frameworks, pure ES6+ JavaScript
- **Fetch API**: RESTful API communication
- **LocalStorage**: Session persistence

## Key Components

### Authentication Module (`Auth`)
Handles login, logout, and session management:
- `init()`: Initialize auth state from localStorage
- `login()`: Authenticate user and store token
- `logout()`: Clear session and redirect to login
- `showDashboard()`: Display main dashboard after login

### API Service (`API`)
Manages all API communications:
- `request()`: Generic API request handler
- `login()`: POST /api/auth/login
- `getConfig()`: GET /api/config/
- `updateConfig()`: PUT /api/config/
- `getBotStatus()`: GET /api/bot/status
- `controlBot()`: POST /api/bot/control
- `getBotStats()`: GET /api/bot/stats
- `getHealth()`: GET /health

### Dashboard Module (`Dashboard`)
Controls the main dashboard functionality:
- `init()`: Load initial dashboard data
- `loadConfig()`: Fetch and display configuration
- `updateConfig()`: Save configuration changes
- `refreshStatus()`: Update bot status and statistics
- `controlBot()`: Execute bot control commands
- `loadHealth()`: Display system health information

### Utilities (`Utils`)
Helper functions for common operations:
- `showScreen()`: Switch between login and dashboard
- `toggleElement()`: Show/hide elements
- `setText()`: Update element text content
- `formatUptime()`: Format seconds to human-readable time
- `getAuthHeaders()`: Generate authorization headers

## API Integration

All API calls use the base URL from `window.location.origin` and include:

### Endpoints Used
- `POST /api/auth/login` - User authentication
- `GET /api/config/` - Fetch configuration
- `PUT /api/config/` - Update configuration
- `POST /api/config/reload` - Reload from file
- `GET /api/config/validate` - Validate settings
- `GET /api/bot/status` - Bot status
- `POST /api/bot/control` - Control bot
- `GET /api/bot/stats` - Statistics
- `GET /health` - System health

### Authentication
JWT token is included in all authenticated requests:
```javascript
Authorization: Bearer <token>
```

### Error Handling
- 401 responses trigger automatic logout
- All errors are caught and displayed to user
- Network errors handled gracefully

## Responsive Design

The interface is fully responsive and works on:
- Desktop (1200px+)
- Tablet (768px - 1199px)
- Mobile (< 768px)

### Mobile Optimizations
- Single column layout
- Full-width buttons
- Optimized spacing
- Touch-friendly controls

## Customization

### Colors
All colors are defined as CSS variables in `:root`:
```css
--primary-color: #5865f2;
--success-color: #43b581;
--warning-color: #faa61a;
--danger-color: #f04747;
--secondary-color: #747f8d;
```

### Styling
Modify `style.css` to customize appearance:
- Change color scheme in `:root` variables
- Adjust spacing and sizing
- Modify animations and transitions

### Functionality
Modify `app.js` to add features:
- Add new API endpoints
- Customize refresh intervals
- Add new dashboard widgets
- Extend form validation

## Usage

1. **Start the FastAPI server**:
   ```bash
   python run_api.py
   ```

2. **Access the interface**:
   Open browser to `http://localhost:8000`

3. **Login**:
   - Username: from `ADMIN_USERNAME` env variable
   - Password: from `ADMIN_PASSWORD` env variable

4. **Manage Bot**:
   - View status in real-time
   - Update configuration as needed
   - Control bot operations

## Development

### Adding New Features

1. **Add HTML Elements**:
   ```html
   <div id="myNewFeature" class="card">
     <!-- Feature content -->
   </div>
   ```

2. **Add Styling**:
   ```css
   #myNewFeature {
     /* Custom styles */
   }
   ```

3. **Add JavaScript Logic**:
   ```javascript
   const MyFeature = {
     init() {
       // Initialize feature
     }
   };
   ```

4. **Hook into Dashboard**:
   ```javascript
   Dashboard.init = async function() {
     // ... existing code
     await MyFeature.init();
   };
   ```

### Testing

Open browser console to:
- Monitor API calls
- Check for JavaScript errors
- View network requests
- Debug authentication issues

## Security Considerations

1. **Authentication**: Always uses HTTPS in production
2. **Token Storage**: LocalStorage for session persistence
3. **CORS**: Configured on backend for allowed origins
4. **Input Validation**: Client-side validation with server verification
5. **XSS Protection**: No innerHTML usage, only textContent

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+
- Opera 76+

Requires modern JavaScript features:
- ES6+ syntax
- Fetch API
- LocalStorage
- CSS Grid/Flexbox

## Troubleshooting

### Login Fails
- Check browser console for errors
- Verify credentials in .env file
- Check API server is running
- Verify SECRET_KEY is set

### Cannot Load Configuration
- Check authentication token
- Verify API endpoints are responding
- Check browser console for errors

### Status Not Updating
- Check auto-refresh interval
- Verify bot is running
- Check network connection
- Look for JavaScript errors

## Future Enhancements

Potential improvements:
- [ ] WebSocket for real-time updates
- [ ] Advanced statistics charts
- [ ] Log viewer
- [ ] User management
- [ ] Dark mode toggle
- [ ] Multi-language support
- [ ] Configuration backup/restore
- [ ] API key management UI
- [ ] Bot command tester

## License

Part of the Discord AI Bot project.

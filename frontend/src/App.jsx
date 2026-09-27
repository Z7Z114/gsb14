import React, { useState, useEffect } from 'react';
import { Routes, Route, Link, useLocation } from 'react-router-dom';
import {
  AppBar, Toolbar, Typography, Drawer, List, ListItem, ListItemIcon,
  ListItemText, Box, CssBaseline
} from '@mui/material';
import { Home, Sensors, Mic, Description } from '@mui/icons-material';
import Dashboard from './pages/Dashboard';
import DetectorList from './pages/DetectorList';
import DetectorDetail from './pages/DetectorDetail';
import SessionDetail from './pages/SessionDetail';
import TranscriptionView from './pages/TranscriptionView';
import SummaryView from './pages/SummaryView';

const drawerWidth = 240;

function App() {
  const [detectors, setDetectors] = useState([]);
  const location = useLocation();

  useEffect(() => {
    fetch('/api/detectors')
      .then(res => res.json())
      .then(data => setDetectors(data))
      .catch(err => console.error('Failed to fetch detectors:', err));
  }, []);

  const menuItems = [
    { text: '仪表盘', icon: <Home />, path: '/' },
    { text: '探测器管理', icon: <Sensors />, path: '/detectors' },
  ];

  return (
    <Box sx={{ display: 'flex' }}>
      <CssBaseline />
      <AppBar position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}>
        <Toolbar>
          <Typography variant="h6" noWrap component="div">
            ⚛️ 地下实验室暗物质探测纪要系统
          </Typography>
        </Toolbar>
      </AppBar>
      <Drawer
        variant="permanent"
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          [`& .MuiDrawer-paper`]: { width: drawerWidth, boxSizing: 'border-box' },
        }}
      >
        <Toolbar />
        <Box sx={{ overflow: 'auto' }}>
          <List>
            {menuItems.map((item) => (
              <ListItem
                button
                component={Link}
                to={item.path}
                key={item.text}
                selected={location.pathname === item.path}
              >
                <ListItemIcon>{item.icon}</ListItemIcon>
                <ListItemText primary={item.text} />
              </ListItem>
            ))}
          </List>
        </Box>
      </Drawer>
      <Box component="main" sx={{ flexGrow: 1, p: 3 }}>
        <Toolbar />
        <Routes>
          <Route path="/" element={<Dashboard detectors={detectors} />} />
          <Route path="/detectors" element={<DetectorList detectors={detectors} setDetectors={setDetectors} />} />
          <Route path="/detectors/:id" element={<DetectorDetail />} />
          <Route path="/sessions/:id" element={<SessionDetail />} />
          <Route path="/recordings/:id/transcriptions" element={<TranscriptionView />} />
          <Route path="/summaries/:id" element={<SummaryView />} />
        </Routes>
      </Box>
    </Box>
  );
}

export default App;

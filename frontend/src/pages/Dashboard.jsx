import React, { useState, useEffect } from 'react';
import { Grid, Card, CardContent, Typography, Box } from '@mui/material';
import { Sensors, Timeline, Mic, Email } from '@mui/icons-material';

function Dashboard({ detectors }) {
  const [stats, setStats] = useState({
    totalDetectors: 0,
    totalSessions: 0,
    pendingTranscriptions: 0,
    emailsSent: 0,
  });

  useEffect(() => {
    setStats(prev => ({
      ...prev,
      totalDetectors: detectors.length,
      totalSessions: detectors.reduce((sum, d) => sum + (d.sessions?.length || 0), 0)
    }));
  }, [detectors]);

  const statCards = [
    { title: '探测器模块', value: stats.totalDetectors, icon: <Sensors sx={{ fontSize: 40 }} />, color: '#1565c0' },
    { title: '运行次数', value: stats.totalSessions, icon: <Timeline sx={{ fontSize: 40 }} />, color: '#00897b' },
    { title: '待处理录音', value: stats.pendingTranscriptions, icon: <Mic sx={{ fontSize: 40 }} />, color: '#ef6c00' },
    { title: '已发送邮件', value: stats.emailsSent, icon: <Email sx={{ fontSize: 40 }} />, color: '#6a1b9a' },
  ];

  return (
    <Box>
      <Typography variant="h4" gutterBottom>仪表盘</Typography>
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {statCards.map((card, index) => (
          <Grid item xs={12} sm={6} md={3} key={index}>
            <Card sx={{ height: '100%' }}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <Box>
                    <Typography color="textSecondary" gutterBottom>{card.title}</Typography>
                    <Typography variant="h3">{card.value}</Typography>
                  </Box>
                  <Box sx={{ color: card.color }}>{card.icon}</Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}

export default Dashboard;

import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  Box, Typography, Button, Card, CardContent, Grid, Typography as T
} from '@mui/material';
import { ArrowBack, Mic, Description } from '@mui/icons-material';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';

function SessionDetail() {
  const { id } = useParams();
  const [session, setSession] = useState(null);
  const [spectra, setSpectra] = useState([]);
  const [events, setEvents] = useState([]);

  useEffect(() => {
    // 运行详情：SessionDetail 通过该接口加载会话信息
    fetch(`/api/detectors/sessions/${id}`)
      .then(res => res.json())
      .then(data => setSession(data))
      .catch(err => console.error('Failed to fetch session:', err));
    fetch(`/api/detectors/sessions/${id}/spectra`)
      .then(res => res.json())
      .then(data => setSpectra(Array.isArray(data) ? data : []))
      .catch(() => {});
    fetch(`/api/detectors/sessions/${id}/events`)
      .then(res => res.json())
      .then(data => setEvents(Array.isArray(data) ? data : []))
      .catch(() => {});
  }, [id]);

  if (!session) {
    return <Typography>加载中...</Typography>;
  }

  return (
    <Box>
      <Button component={Link} to="/detectors" startIcon={<ArrowBack />} sx={{ mb: 2 }}>返回</Button>
      <Typography variant="h4" gutterBottom>{session.run_type || '运行详情'}</Typography>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={2}>
            <Grid item xs={12} sm={6} md={3}>
              <T variant="body2" color="textSecondary">曝光量</T>
              <T variant="body1">{session.exposure_hours} h</T>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <T variant="body2" color="textSecondary">能量阈值</T>
              <T variant="body1">{session.energy_threshold_kev} keV</T>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <T variant="body2" color="textSecondary">探测器</T>
              <T variant="body1">#{session.detector_id}</T>
            </Grid>
            <Grid item xs={12} sm={6} md={3}>
              <T variant="body2" color="textSecondary">备注</T>
              <T variant="body1">{session.notes || '-'}</T>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      <Card sx={{ mb: 3 }}>
        <CardContent>
          <T variant="h6" gutterBottom>本底谱与拟合曲线</T>
          <ResponsiveContainer width="100%" height={320}>
            <LineChart data={spectra}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="energy_kev" label={{ value: '能量 (keV)', position: 'insideBottom', offset: -4 }} />
              <YAxis label={{ value: '计数', angle: -90, position: 'insideLeft' }} />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="counts" name="本底计数" stroke="#1565c0" dot={false} />
              <Line type="monotone" dataKey="fit_value" name="拟合值" stroke="#ef6c00" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <Card>
        <CardContent>
          <T variant="h6" gutterBottom>疑似信号事件（{events.length}）</T>
          {events.map((ev) => (
            <Box key={ev.id} sx={{ mb: 1 }}>
              <T variant="body1">能量 {ev.energy_kev} keV · S1 {ev.s1_pe} PE · S2 {ev.s2_pe} PE</T>
            </Box>
          ))}
        </CardContent>
      </Card>
    </Box>
  );
}

export default SessionDetail;

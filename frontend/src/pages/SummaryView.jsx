import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import {
  Box, Typography, Button, Card, CardContent, Grid, Chip, Paper, Alert
} from '@mui/material';
import { ArrowBack, Email, Description, Science, Timeline, Warning } from '@mui/icons-material';

function SummaryView() {
  const { id } = useParams();
  const [summary, setSummary] = useState(null);
  const [emailStatus, setEmailStatus] = useState(null);

  useEffect(() => {
    fetch(`/api/audio/summaries/${id}`)
      .then(res => res.json())
      .then(data => setSummary(data))
      .catch(err => console.error('Failed to fetch summary:', err));
  }, [id]);

  const handleSendEmail = async () => {
    const response = await fetch(`/api/audio/summaries/${id}/send-email`, { method: 'POST' });
    const data = await response.json();
    setEmailStatus({
      type: response.ok ? 'success' : 'error',
      message: response.ok ? '纪要已发送给物理组' : (data.error || '发送失败')
    });
    setSummary({ ...summary, sent_to_team: true });
  };

  if (!summary) {
    return <Typography>加载中...</Typography>;
  }

  return (
    <Box>
      <Button component={Link} to="/detectors" startIcon={<ArrowBack />} sx={{ mb: 2 }}>返回</Button>
      {emailStatus && <Alert severity={emailStatus.type} sx={{ mb: 2 }}>{emailStatus.message}</Alert>}

      <Card sx={{ mb: 4 }}>
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <Typography variant="h4"><Description sx={{ mr: 1, verticalAlign: 'middle' }} />运行纪要</Typography>
            {summary.sent_to_team ? (
              <Chip label="已发送" color="success" variant="outlined" />
            ) : (
              <Button variant="contained" startIcon={<Email />} onClick={handleSendEmail}>发送给物理组</Button>
            )}
          </Box>
        </CardContent>
      </Card>

      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Card><CardContent>
            <Typography variant="h6" gutterBottom>运行摘要</Typography>
            <Paper variant="outlined" sx={{ p: 2, bgcolor: '#f5f5f5' }}>
              <Typography sx={{ whiteSpace: 'pre-wrap' }}>{summary.summary_text}</Typography>
            </Paper>
          </CardContent></Card>
        </Grid>
        <Grid item xs={12} md={6}>
          <Card><CardContent>
            <Typography variant="h6" gutterBottom><Warning color="error" /> 异常事件分析</Typography>
            <Paper variant="outlined" sx={{ p: 2, bgcolor: '#ffebee' }}>
              <Typography sx={{ whiteSpace: 'pre-wrap' }}>{summary.anomaly_analysis}</Typography>
            </Paper>
          </CardContent></Card>
        </Grid>
        <Grid item xs={12} md={6}>
          <Card><CardContent>
            <Typography variant="h6" gutterBottom><Timeline color="secondary" /> 后续运行计划</Typography>
            <Paper variant="outlined" sx={{ p: 2, bgcolor: '#e8f5e9' }}>
              <Typography sx={{ whiteSpace: 'pre-wrap' }}>{summary.run_plan}</Typography>
            </Paper>
          </CardContent></Card>
        </Grid>
        <Grid item xs={12} md={6}>
          <Card><CardContent>
            <Typography variant="h6" gutterBottom><Science color="primary" /> 校准注意事项</Typography>
            <Paper variant="outlined" sx={{ p: 2 }}>
              <Typography sx={{ whiteSpace: 'pre-wrap' }}>{summary.calibration_notes}</Typography>
            </Paper>
          </CardContent></Card>
        </Grid>
        <Grid item xs={12} md={6}>
          <Card><CardContent>
            <Typography variant="h6" gutterBottom>关键物理术语</Typography>
            <Box>
              {(summary.key_terms || []).map((t, i) => (
                <Chip key={i} label={t} color="primary" variant="outlined" sx={{ mr: 1, mb: 1 }} />
              ))}
            </Box>
          </CardContent></Card>
        </Grid>
      </Grid>
    </Box>
  );
}

export default SummaryView;

import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Box, Typography, Button, Grid, Card, CardContent, CardActions,
  Dialog, DialogTitle, DialogContent, DialogActions, TextField, MenuItem
} from '@mui/material';
import { Add, Sensors } from '@mui/icons-material';

function DetectorList({ detectors, setDetectors }) {
  const [open, setOpen] = useState(false);
  const [formData, setFormData] = useState({
    name: '', module_code: '', target_material: '', location: '', status: 'commissioning'
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    const response = await fetch('/api/detectors', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(formData),
    });
    const data = await response.json();
    if (data.id) {
      setDetectors([...detectors, { ...formData, id: data.id }]);
      setOpen(false);
      setFormData({ name: '', module_code: '', target_material: '', location: '', status: 'commissioning' });
    }
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 3 }}>
        <Typography variant="h4">探测器管理</Typography>
        <Button variant="contained" startIcon={<Add />} onClick={() => setOpen(true)}>
          注册探测器
        </Button>
      </Box>
      <Grid container spacing={3}>
        {detectors.map((detector) => (
          <Grid item xs={12} sm={6} md={4} key={detector.id}>
            <Card sx={{ height: '100%' }}>
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <Sensors sx={{ fontSize: 36, color: '#1565c0', mr: 2 }} />
                  <Box>
                    <Typography variant="h6">{detector.name}</Typography>
                    <Typography variant="body2" color="textSecondary">
                      {detector.module_code || '未编号'}
                    </Typography>
                  </Box>
                </Box>
                <Typography variant="body2" color="textSecondary">靶物质</Typography>
                <Typography variant="body1">{detector.target_material || '-'}</Typography>
                <Typography variant="body2" color="textSecondary">位置</Typography>
                <Typography variant="body1">{detector.location || '-'}</Typography>
              </CardContent>
              <CardActions>
                <Button component={Link} to={`/detectors/${detector.id}`} size="small">查看详情</Button>
              </CardActions>
            </Card>
          </Grid>
        ))}
      </Grid>

      <Dialog open={open} onClose={() => setOpen(false)}>
        <form onSubmit={handleSubmit}>
          <DialogTitle>注册新探测器</DialogTitle>
          <DialogContent>
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 2, minWidth: 320 }}>
              <TextField label="名称" required value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })} />
              <TextField label="模块编号" value={formData.module_code}
                onChange={(e) => setFormData({ ...formData, module_code: e.target.value })} />
              <TextField label="靶物质" value={formData.target_material}
                onChange={(e) => setFormData({ ...formData, target_material: e.target.value })} />
              <TextField label="位置" value={formData.location}
                onChange={(e) => setFormData({ ...formData, location: e.target.value })} />
              <TextField select label="状态" value={formData.status}
                onChange={(e) => setFormData({ ...formData, status: e.target.value })}>
                <MenuItem value="commissioning">调试中</MenuItem>
                <MenuItem value="running">运行中</MenuItem>
                <MenuItem value="maintenance">维护中</MenuItem>
              </TextField>
            </Box>
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setOpen(false)}>取消</Button>
            <Button type="submit" variant="contained">注册</Button>
          </DialogActions>
        </form>
      </Dialog>
    </Box>
  );
}

export default DetectorList;
